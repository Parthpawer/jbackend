import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OrderStatusHistory

logger = logging.getLogger('apps.orders')


@receiver(post_save, sender=OrderStatusHistory)
def handle_status_change(sender, instance, created, **kwargs):
    """Trigger notifications when order status changes."""
    if not created:
        return

    order = instance.order
    user = order.user
    status_val = instance.status

    # Import notification functions
    from apps.notifications.whatsapp import send_whatsapp_notification
    from apps.notifications.email import send_order_email

    try:
        if status_val == 'confirmed':
            send_whatsapp_notification(
                phone=user.phone,
                template='order_confirmed',
                order=order,
                user=user,
            )
            send_order_email(
                template='order_confirmed',
                order=order,
                user=user,
            )
            logger.info(f'Notifications sent for order #{str(order.id)[:8]} — confirmed')

        elif status_val == 'shipped':
            send_whatsapp_notification(
                phone=user.phone,
                template='order_shipped',
                order=order,
                user=user,
            )
            send_order_email(
                template='order_shipped',
                order=order,
                user=user,
            )
            logger.info(f'Notifications sent for order #{str(order.id)[:8]} — shipped')

        elif status_val == 'delivered':
            send_whatsapp_notification(
                phone=user.phone,
                template='order_delivered',
                order=order,
                user=user,
            )
            logger.info(f'Notification sent for order #{str(order.id)[:8]} — delivered')

    except Exception as e:
        logger.error(f'Notification failed for order #{str(order.id)[:8]}: {e}')
