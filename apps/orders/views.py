import hashlib
import hmac
import logging
from decimal import Decimal

import razorpay
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.models import Cart
from apps.users.models import Address
from .models import Order, OrderItem, OrderStatusHistory, PaymentHistory
from .serializers import (
    CreateOrderSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    PaymentHistorySerializer,
)

logger = logging.getLogger('apps.orders')


def api_response(data=None, message='Success', success=True, status_code=status.HTTP_200_OK):
    return Response({'success': success, 'data': data, 'message': message}, status=status_code)


def api_error(error='An error occurred', details=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'error': error, 'details': details or {}}, status=status_code)


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


class CreateOrderView(APIView):
    """POST /api/orders/create/ — Create order from cart, initiate Razorpay payment."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error('Validation failed', serializer.errors)

        user = request.user
        address = get_object_or_404(Address, pk=serializer.validated_data['address_id'], user=user)

        # Get user's cart
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return api_error('Cart is empty')

        cart_items = cart.items.select_related('variant__product').all()
        if not cart_items.exists():
            return api_error('Cart is empty')

        # Validate stock
        for item in cart_items:
            if item.variant.stock < item.quantity:
                return api_error(
                    f'{item.variant.product.name} ({item.variant.metal_type}) has only '
                    f'{item.variant.stock} items in stock'
                )

        # Calculate subtotal
        subtotal = sum(item.variant.price * item.quantity for item in cart_items)

        # Apply discount if provided
        discount_amount = Decimal('0.00')
        discount_code = serializer.validated_data.get('discount_code', '').strip()
        if discount_code:
            from apps.products.models import Product  # avoid circular
            try:
                from django.utils import timezone as tz
                from django.db.models import Q

                # Import Discount model - we'll create it inline since it's referenced in the schema
                # For now, discount logic is optional and can be extended
                pass
            except Exception:
                pass

        # BUSINESS RULE: Shipping is ALWAYS free
        shipping_charge = Decimal('0.00')
        total_amount = subtotal - discount_amount

        # Create order
        order = Order.objects.create(
            user=user,
            address=address,
            status='pending',
            subtotal_amount=subtotal,
            shipping_charge=shipping_charge,
            discount_amount=discount_amount,
            total_amount=total_amount,
        )

        # Create order items with price snapshot
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                price_at_purchase=item.variant.price,
            )

        # Log initial status
        OrderStatusHistory.objects.create(
            order=order,
            status='pending',
            note='Order created, awaiting payment',
        )

        # Create Razorpay order
        try:
            client = get_razorpay_client()
            razorpay_order = client.order.create({
                'amount': int(total_amount * 100),  # Amount in paise
                'currency': 'INR',
                'receipt': str(order.id),
                'notes': {
                    'order_id': str(order.id),
                    'user_email': user.email,
                }
            })

            order.razorpay_order_id = razorpay_order['id']
            order.save()

            # Create PaymentHistory record
            PaymentHistory.objects.create(
                order=order,
                user=user,
                razorpay_order_id=razorpay_order['id'],
                amount=total_amount,
                status='initiated',
            )

        except Exception as e:
            logger.error(f'Razorpay order creation failed: {e}')
            order.delete()
            return api_error('Payment gateway error. Please try again.',
                             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return api_response({
            'order_id': str(order.id),
            'razorpay_order_id': razorpay_order['id'],
            'amount': float(total_amount),
            'currency': 'INR',
            'key_id': settings.RAZORPAY_KEY_ID,
            'user': {
                'name': user.name,
                'email': user.email,
                'phone': user.phone,
            }
        }, 'Order created', status_code=status.HTTP_201_CREATED)


class VerifyPaymentView(APIView):
    """POST /api/orders/verify-payment/ — Verify Razorpay payment signature."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return api_error('Missing payment verification data')

        # Verify signature
        try:
            client = get_razorpay_client()
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            })
        except razorpay.errors.SignatureVerificationError:
            # Update payment history
            PaymentHistory.objects.filter(
                razorpay_order_id=razorpay_order_id
            ).update(
                status='failed',
                failure_reason='Signature verification failed',
                completed_at=timezone.now(),
            )
            return api_error('Payment verification failed', status_code=status.HTTP_400_BAD_REQUEST)

        # Payment verified — update order
        try:
            order = Order.objects.get(razorpay_order_id=razorpay_order_id, user=request.user)
        except Order.DoesNotExist:
            return api_error('Order not found', status_code=status.HTTP_404_NOT_FOUND)

        order.razorpay_payment_id = razorpay_payment_id
        order.status = 'confirmed'
        order.save()

        # Update payment history
        payment = PaymentHistory.objects.filter(
            razorpay_order_id=razorpay_order_id
        ).order_by('-initiated_at').first()

        if payment:
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'success'
            payment.completed_at = timezone.now()
            # Fetch payment details from Razorpay
            try:
                payment_detail = client.payment.fetch(razorpay_payment_id)
                payment.payment_method = payment_detail.get('method', '')
                payment.gateway_response = payment_detail
            except Exception:
                pass
            payment.save()

        # Log status change (triggers notification signal)
        OrderStatusHistory.objects.create(
            order=order,
            status='confirmed',
            note='Payment verified successfully',
        )

        # Deduct stock
        for item in order.items.select_related('variant').all():
            variant = item.variant
            variant.stock -= item.quantity
            variant.save()

        # Clear cart
        try:
            cart = Cart.objects.get(user=request.user)
            cart.items.all().delete()
        except Cart.DoesNotExist:
            pass

        return api_response(
            OrderDetailSerializer(order).data,
            'Payment verified and order confirmed'
        )


class OrderListView(APIView):
    """GET /api/orders/ — List user's orders."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user)
        serializer = OrderListSerializer(orders, many=True)
        return api_response(serializer.data)


class OrderDetailView(APIView):
    """GET /api/orders/{id}/ — Order detail."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        serializer = OrderDetailSerializer(order)
        return api_response(serializer.data)


class OrderCancelView(APIView):
    """POST /api/orders/{id}/cancel/ — Cancel an order."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)

        if order.status not in ('pending', 'confirmed'):
            return api_error('Order can only be cancelled when pending or confirmed')

        order.status = 'cancelled'
        order.save()

        OrderStatusHistory.objects.create(
            order=order,
            status='cancelled',
            note='Cancelled by customer',
        )

        # Restore stock
        for item in order.items.select_related('variant').all():
            variant = item.variant
            variant.stock += item.quantity
            variant.save()

        return api_response(OrderDetailSerializer(order).data, 'Order cancelled')


class OrderPaymentsView(APIView):
    """GET /api/orders/{id}/payments/ — Payment history for an order."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        payments = PaymentHistory.objects.filter(order=order)
        serializer = PaymentHistorySerializer(payments, many=True)
        return api_response(serializer.data)


class RazorpayWebhookView(APIView):
    """POST /api/orders/webhook/ — Handle Razorpay webhook events."""
    permission_classes = [AllowAny]

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        webhook_signature = request.headers.get('X-Razorpay-Signature', '')
        webhook_body = request.body.decode('utf-8')

        # Verify webhook signature
        if webhook_secret:
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                webhook_body.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_signature, webhook_signature):
                return api_error('Invalid webhook signature', status_code=status.HTTP_400_BAD_REQUEST)

        event = request.data.get('event', '')
        payload = request.data.get('payload', {})

        if event == 'payment.captured':
            self._handle_payment_captured(payload)
        elif event == 'payment.failed':
            self._handle_payment_failed(payload)
        elif event == 'refund.created':
            self._handle_refund_created(payload)

        return Response({'status': 'ok'})

    def _handle_payment_captured(self, payload):
        payment_entity = payload.get('payment', {}).get('entity', {})
        razorpay_order_id = payment_entity.get('order_id')

        PaymentHistory.objects.filter(
            razorpay_order_id=razorpay_order_id,
            status='initiated'
        ).update(
            status='success',
            razorpay_payment_id=payment_entity.get('id'),
            payment_method=payment_entity.get('method'),
            gateway_response=payment_entity,
            completed_at=timezone.now(),
        )

    def _handle_payment_failed(self, payload):
        payment_entity = payload.get('payment', {}).get('entity', {})
        razorpay_order_id = payment_entity.get('order_id')
        error = payment_entity.get('error_description', 'Payment failed')

        PaymentHistory.objects.filter(
            razorpay_order_id=razorpay_order_id,
            status='initiated'
        ).update(
            status='failed',
            failure_reason=error,
            gateway_response=payment_entity,
            completed_at=timezone.now(),
        )

    def _handle_refund_created(self, payload):
        refund_entity = payload.get('refund', {}).get('entity', {})
        payment_id = refund_entity.get('payment_id')

        payment = PaymentHistory.objects.filter(
            razorpay_payment_id=payment_id,
            status='success'
        ).first()

        if payment:
            refund_amount = Decimal(str(refund_entity.get('amount', 0))) / 100
            payment.refund_id = refund_entity.get('id')
            payment.refund_amount = refund_amount
            payment.status = 'refunded' if refund_amount >= payment.amount else 'partially_refunded'
            payment.save()
