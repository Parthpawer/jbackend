"""
Email notifications using Django's built-in email (smtplib backend).
"""
import logging
from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger('apps.notifications')


def send_order_email(template, order, user):
    """Send a transactional email for order events."""
    if not user.email:
        logger.warning('Email notification skipped — no email address')
        return False

    if template == 'order_confirmed':
        subject = f'Order Confirmed — #{str(order.id)[:8].upper()}'
        body = _build_confirmation_email(order, user)
    elif template == 'order_shipped':
        subject = f'Your Order Has Shipped — #{str(order.id)[:8].upper()}'
        body = _build_shipped_email(order, user)
    else:
        logger.warning(f'Unknown email template: {template}')
        return False

    try:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.content_subtype = 'html'
        email.send(fail_silently=False)
        logger.info(f'Email sent to {user.email} — template: {template}')
        return True
    except Exception as e:
        logger.error(f'Email send failed to {user.email}: {e}')
        return False


def _build_confirmation_email(order, user):
    """Build HTML email for order confirmation."""
    items_html = ''
    for item in order.items.select_related('variant__product').all():
        items_html += f'''
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #F2C4D0;">
                {item.variant.product.name}<br>
                <small style="color: #6B3A4A;">{item.variant.metal_type}
                {f" | Size {item.variant.size}" if item.variant.size else ""}</small>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #F2C4D0; text-align: center;">{item.quantity}</td>
            <td style="padding: 12px; border-bottom: 1px solid #F2C4D0; text-align: right;">₹{item.line_total:,.2f}</td>
        </tr>
        '''

    address = order.address
    address_html = ''
    if address:
        address_html = f'{address.full_name}<br>{address.street}<br>{address.city}, {address.state} — {address.pincode}'

    return f'''
    <div style="font-family: 'Jost', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #FAF0F3;">
        <div style="background: #8B1D52; padding: 24px; text-align: center;">
            <h1 style="color: #fff; font-family: 'Cormorant Garamond', serif; margin: 0; font-size: 28px;">
                {settings.STORE_NAME}
            </h1>
        </div>

        <div style="padding: 32px 24px;">
            <h2 style="color: #8B1D52; font-family: 'Cormorant Garamond', serif; margin-top: 0;">
                Thank you, {user.name}!
            </h2>
            <p style="color: #1A0A10;">Your order <strong>#{str(order.id)[:8].upper()}</strong> has been confirmed.</p>

            <table style="width: 100%; border-collapse: collapse; margin: 24px 0;">
                <thead>
                    <tr style="background: #F2C4D0;">
                        <th style="padding: 12px; text-align: left; color: #8B1D52;">Item</th>
                        <th style="padding: 12px; text-align: center; color: #8B1D52;">Qty</th>
                        <th style="padding: 12px; text-align: right; color: #8B1D52;">Price</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <div style="text-align: right; margin: 16px 0;">
                <p style="margin: 4px 0; color: #6B3A4A;">Subtotal: ₹{order.subtotal_amount:,.2f}</p>
                <p style="margin: 4px 0; color: #27ae60; font-weight: 500;">Shipping: FREE</p>
                <p style="margin: 8px 0 0; font-size: 20px; color: #8B1D52; font-weight: 600;">
                    Total: ₹{order.total_amount:,.2f}
                </p>
            </div>

            <div style="background: #fff; padding: 16px; border-radius: 8px; margin-top: 24px;">
                <h3 style="color: #8B1D52; margin-top: 0; font-size: 14px; text-transform: uppercase;">Shipping To</h3>
                <p style="color: #1A0A10; margin-bottom: 0;">{address_html}</p>
            </div>
        </div>

        <div style="background: #1A0A10; padding: 24px; text-align: center;">
            <p style="color: #C96B8A; margin: 0; font-size: 14px;">
                © {settings.STORE_NAME} · Free Shipping on All Orders · BIS Hallmarked
            </p>
        </div>
    </div>
    '''


def _build_shipped_email(order, user):
    """Build HTML email for order shipped."""
    return f'''
    <div style="font-family: 'Jost', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #FAF0F3;">
        <div style="background: #8B1D52; padding: 24px; text-align: center;">
            <h1 style="color: #fff; font-family: 'Cormorant Garamond', serif; margin: 0; font-size: 28px;">
                {settings.STORE_NAME}
            </h1>
        </div>

        <div style="padding: 32px 24px; text-align: center;">
            <div style="font-size: 48px; margin-bottom: 16px;">📦</div>
            <h2 style="color: #8B1D52; font-family: 'Cormorant Garamond', serif;">
                Your Order is on its Way!
            </h2>
            <p style="color: #1A0A10;">
                Hi {user.name}, your order <strong>#{str(order.id)[:8].upper()}</strong> has been shipped!
            </p>
            <p style="color: #6B3A4A;">Expected delivery: 3-5 business days</p>

            <div style="background: #fff; padding: 20px; border-radius: 8px; margin: 24px 0; display: inline-block;">
                <p style="margin: 0; color: #6B3A4A; font-size: 14px;">Order Total</p>
                <p style="margin: 8px 0 0; font-size: 24px; color: #8B1D52; font-weight: 600;">
                    ₹{order.total_amount:,.2f}
                </p>
            </div>
        </div>

        <div style="background: #1A0A10; padding: 24px; text-align: center;">
            <p style="color: #C96B8A; margin: 0; font-size: 14px;">
                © {settings.STORE_NAME} · Free Shipping on All Orders
            </p>
        </div>
    </div>
    '''
