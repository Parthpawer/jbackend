import uuid
from django.db import models
from django.conf import settings


class Order(models.Model):
    """Customer order."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey('users.Address', on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{str(self.id)[:8]} — {self.user.name}'

    def save(self, *args, **kwargs):
        # BUSINESS RULE: Shipping is ALWAYS free
        self.shipping_charge = 0.00
        # Total = subtotal - discount (no shipping)
        self.total_amount = self.subtotal_amount - self.discount_amount
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Line item in an order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'order_items'
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        variant_name = self.variant.product.name if self.variant else 'Deleted Product'
        return f'{variant_name} × {self.quantity}'

    @property
    def line_total(self):
        return self.price_at_purchase * self.quantity


class OrderStatusHistory(models.Model):
    """Audit trail of order status changes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    note = models.TextField(blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'order_status_history'
        verbose_name = 'Order Status History'
        verbose_name_plural = 'Order Status History'
        ordering = ['-changed_at']

    def __str__(self):
        return f'Order #{str(self.order.id)[:8]} → {self.status}'


class PaymentHistory(models.Model):
    """Record of every payment attempt."""

    PAYMENT_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    razorpay_order_id = models.CharField(max_length=255)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=500, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='initiated')
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)
    refund_id = models.CharField(max_length=255, blank=True, null=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    gateway_response = models.JSONField(blank=True, null=True)
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_history'
        verbose_name = 'Payment History'
        verbose_name_plural = 'Payment History'
        ordering = ['-initiated_at']

    def __str__(self):
        return f'Payment {self.status} — ₹{self.amount} for Order #{str(self.order.id)[:8]}'
