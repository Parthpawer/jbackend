from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusHistory, PaymentHistory
from apps.products.serializers import ProductVariantSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    variant_detail = ProductVariantSerializer(source='variant', read_only=True)
    product_name = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            'id', 'variant', 'variant_detail', 'product_name',
            'primary_image', 'quantity', 'price_at_purchase', 'line_total'
        )

    def get_product_name(self, obj):
        return obj.variant.product.name if obj.variant else 'Deleted Product'

    def get_primary_image(self, obj):
        if not obj.variant:
            return ''
        img = obj.variant.product.images.filter(is_primary=True).first()
        return img.cloudinary_url if img else ''


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ('id', 'status', 'note', 'changed_at')


class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = (
            'id', 'razorpay_order_id', 'razorpay_payment_id', 'amount',
            'currency', 'status', 'payment_method', 'failure_reason',
            'initiated_at', 'completed_at'
        )


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight order serializer for list views."""
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            'id', 'status', 'subtotal_amount', 'shipping_charge',
            'total_amount', 'item_count', 'created_at'
        )

    def get_item_count(self, obj):
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Full order serializer with items, status history, and address."""
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    address_detail = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            'id', 'status', 'subtotal_amount', 'shipping_charge',
            'discount_amount', 'total_amount', 'razorpay_order_id',
            'razorpay_payment_id', 'items', 'status_history',
            'address_detail', 'created_at'
        )

    def get_address_detail(self, obj):
        if not obj.address:
            return None
        return {
            'full_name': obj.address.full_name,
            'street': obj.address.street,
            'city': obj.address.city,
            'state': obj.address.state,
            'pincode': obj.address.pincode,
        }


class CreateOrderSerializer(serializers.Serializer):
    address_id = serializers.UUIDField()
    discount_code = serializers.CharField(required=False, allow_blank=True, default='')
