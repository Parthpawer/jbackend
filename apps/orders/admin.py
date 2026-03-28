from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory, PaymentHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('variant', 'quantity', 'price_at_purchase', 'line_total')

    def line_total(self, obj):
        return obj.line_total
    line_total.short_description = 'Line Total'


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('status', 'note', 'changed_at')


class PaymentHistoryInline(admin.TabularInline):
    model = PaymentHistory
    extra = 0
    readonly_fields = (
        'razorpay_order_id', 'razorpay_payment_id', 'amount',
        'currency', 'status', 'payment_method', 'failure_reason',
        'initiated_at', 'completed_at'
    )
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('short_id', 'user', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'user__name', 'user__email', 'razorpay_order_id')
    readonly_fields = (
        'id', 'user', 'subtotal_amount', 'shipping_charge',
        'discount_amount', 'total_amount', 'razorpay_order_id',
        'razorpay_payment_id', 'created_at', 'updated_at'
    )
    inlines = [OrderItemInline, OrderStatusHistoryInline, PaymentHistoryInline]
    actions = ['mark_confirmed', 'mark_processing', 'mark_shipped', 'mark_delivered']

    def short_id(self, obj):
        return str(obj.id)[:8]
    short_id.short_description = 'Order ID'

    @admin.action(description='Mark as Confirmed')
    def mark_confirmed(self, request, queryset):
        self._update_status(queryset, 'confirmed', 'Confirmed by admin')

    @admin.action(description='Mark as Processing')
    def mark_processing(self, request, queryset):
        self._update_status(queryset, 'processing', 'Processing started by admin')

    @admin.action(description='Mark as Shipped')
    def mark_shipped(self, request, queryset):
        self._update_status(queryset, 'shipped', 'Shipped by admin')

    @admin.action(description='Mark as Delivered')
    def mark_delivered(self, request, queryset):
        self._update_status(queryset, 'delivered', 'Delivered — confirmed by admin')

    def _update_status(self, queryset, new_status, note):
        for order in queryset:
            order.status = new_status
            order.save()
            OrderStatusHistory.objects.create(
                order=order,
                status=new_status,
                note=note,
            )


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'status', 'payment_method', 'initiated_at')
    list_filter = ('status', 'payment_method')
    readonly_fields = (
        'order', 'user', 'razorpay_order_id', 'razorpay_payment_id',
        'razorpay_signature', 'amount', 'currency', 'status',
        'payment_method', 'failure_reason', 'refund_id', 'refund_amount',
        'gateway_response', 'initiated_at', 'completed_at'
    )
