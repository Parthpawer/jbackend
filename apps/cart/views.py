from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemCreateSerializer, CartItemUpdateSerializer
from apps.products.models import ProductVariant


def api_response(data=None, message='Success', success=True, status_code=status.HTTP_200_OK):
    return Response({'success': success, 'data': data, 'message': message}, status=status_code)


def api_error(error='An error occurred', details=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'error': error, 'details': details or {}}, status=status_code)


class CartView(APIView):
    """GET /api/cart/ — Get user's cart."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return api_response(serializer.data)


class CartItemAddView(APIView):
    """POST /api/cart/items/ — Add item to cart."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error('Validation failed', serializer.errors)

        variant = get_object_or_404(ProductVariant, pk=serializer.validated_data['variant_id'])
        quantity = serializer.validated_data['quantity']

        if variant.stock < quantity:
            return api_error(f'Only {variant.stock} items available in stock')

        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Update quantity if item already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, variant=variant,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            if cart_item.quantity > variant.stock:
                return api_error(f'Cannot add more. Only {variant.stock} available.')
            cart_item.save()

        cart.save()  # Update timestamp
        return api_response(CartSerializer(cart).data, 'Item added to cart')


class CartItemUpdateView(APIView):
    """PUT /api/cart/items/{id}/ — Update item quantity."""
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, pk=pk, cart=cart)

        serializer = CartItemUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error('Validation failed', serializer.errors)

        quantity = serializer.validated_data['quantity']
        if quantity > cart_item.variant.stock:
            return api_error(f'Only {cart_item.variant.stock} available in stock')

        cart_item.quantity = quantity
        cart_item.save()
        cart.save()
        return api_response(CartSerializer(cart).data, 'Cart updated')


class CartItemDeleteView(APIView):
    """DELETE /api/cart/items/{id}/ — Remove item from cart."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, pk=pk, cart=cart)
        cart_item.delete()
        cart.save()
        return api_response(CartSerializer(cart).data, 'Item removed from cart')


class CartClearView(APIView):
    """DELETE /api/cart/clear/ — Clear all items from cart."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()
        cart.save()
        return api_response(CartSerializer(cart).data, 'Cart cleared')
