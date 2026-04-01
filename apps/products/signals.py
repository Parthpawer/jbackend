import requests
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import Product, Category, Subcategory, ProductVariant, ProductImage, InstagramPost, HeroSlider

def revalidate_nextjs(tags):
    """
    Pings the Next.js frontend to purge its cache globally so price/stock
    updates reflect immediately without waiting for the 1-hour static cache timer.
    """
    if not hasattr(settings, 'FRONTEND_URL') or not hasattr(settings, 'REVALIDATION_SECRET'):
        return

    secret = getattr(settings, 'REVALIDATION_SECRET', '')
    if not secret:
        return

    # Don't block the save if the frontend is down
    for tag in tags:
        try:
            requests.post(
                f"{settings.FRONTEND_URL}/api/revalidate",
                json={"secret": secret, "tag": tag},
                timeout=3  # 3 second timeout so Django admin doesn't hang
            )
        except Exception as e:
            import logging
            logging.error(f"Failed to revalidate Next.js cache for tag {tag}: {e}")


@receiver([post_save, post_delete], sender=Product)
@receiver([post_save, post_delete], sender=ProductVariant)
@receiver([post_save, post_delete], sender=ProductImage)
def product_changed(sender, instance, **kwargs):
    # Purge the globally cached 'products' tag
    revalidate_nextjs(['products'])


@receiver([post_save, post_delete], sender=Category)
@receiver([post_save, post_delete], sender=Subcategory)
def category_changed(sender, instance, **kwargs):
    # Purge BOTH 'categories' and 'products' since categories affect product navigation
    revalidate_nextjs(['categories', 'products'])


@receiver([post_save, post_delete], sender=InstagramPost)
def instagram_post_changed(sender, instance, **kwargs):
    revalidate_nextjs(['instagram'])


@receiver([post_save, post_delete], sender=HeroSlider)
def hero_slider_changed(sender, instance, **kwargs):
    revalidate_nextjs(['hero'])
