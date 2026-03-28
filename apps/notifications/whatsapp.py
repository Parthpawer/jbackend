"""
WhatsApp notification via Meta Cloud API.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger('apps.notifications')

WHATSAPP_API_URL = 'https://graph.facebook.com/v18.0/{phone_id}/messages'

TEMPLATES = {
    'order_confirmed': (
        'Hello {name}, your order #{order_id} has been confirmed! '
        'Total: ₹{amount}. We\'ll notify you when it ships. '
        '— {store_name}'
    ),
    'order_shipped': (
        'Great news {name}! Your order #{order_id} has been shipped. '
        'Expected delivery: 3-5 business days. '
        '— {store_name}'
    ),
    'order_delivered': (
        'Your order #{order_id} has been delivered! '
        'We hope you love your jewelry. Reply to share feedback. '
        '— {store_name}'
    ),
}


def send_whatsapp_notification(phone, template, order, user):
    """Send a WhatsApp message using Meta Cloud API."""
    if not phone or not settings.WHATSAPP_API_TOKEN:
        logger.warning('WhatsApp notification skipped — missing phone or API token')
        return False

    # Ensure phone has country code
    if not phone.startswith('+'):
        phone = f'+91{phone}'

    message = TEMPLATES.get(template, '').format(
        name=user.name,
        order_id=str(order.id)[:8].upper(),
        amount=f'{order.total_amount:,.2f}',
        store_name=settings.STORE_NAME,
    )

    if not message:
        logger.error(f'Unknown WhatsApp template: {template}')
        return False

    url = WHATSAPP_API_URL.format(phone_id=settings.WHATSAPP_PHONE_NUMBER_ID)
    headers = {
        'Authorization': f'Bearer {settings.WHATSAPP_API_TOKEN}',
        'Content-Type': 'application/json',
    }
    payload = {
        'messaging_product': 'whatsapp',
        'to': phone.replace('+', ''),
        'type': 'text',
        'text': {'body': message},
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f'WhatsApp sent to {phone} — template: {template}')
        return True
    except requests.RequestException as e:
        logger.error(f'WhatsApp send failed: {e}')
        return False
