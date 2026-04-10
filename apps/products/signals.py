import logging
import requests
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings

logger = logging.getLogger(__name__)


def revalidate_nextjs(tags):
    """
    Calls the Next.js /api/revalidate endpoint to purge its ISR cache
    for the given tags. Called after any admin save/delete on content
    that is displayed on cached pages (homepage sections, etc.).
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', '')
    secret = getattr(settings, 'REVALIDATION_SECRET', '')

    if not frontend_url or not secret:
        logger.warning(
            "Next.js revalidation skipped: FRONTEND_URL or REVALIDATION_SECRET "
            "is not set in settings/environment variables."
        )
        return

    frontend_url = frontend_url.rstrip('/')

    for tag in tags:
        try:
            response = requests.post(
                f"{frontend_url}/api/revalidate",
                json={"secret": secret, "tag": tag},
                timeout=5,
            )
            if response.status_code == 200:
                logger.info("Revalidated Next.js cache tag: '%s'", tag)
            elif response.status_code == 401:
                logger.error(
                    "Revalidation unauthorized for tag '%s'. "
                    "Check that REVALIDATION_SECRET matches on both Django and Vercel.",
                    tag,
                )
            else:
                logger.warning(
                    "Revalidation returned %s for tag '%s': %s",
                    response.status_code,
                    tag,
                    response.text,
                )
        except requests.exceptions.ConnectionError:
            logger.error(
                "Could not connect to Next.js frontend at %s to revalidate tag '%s'. "
                "Is FRONTEND_URL set correctly?",
                frontend_url,
                tag,
            )
        except Exception as e:
            logger.error("Unexpected error revalidating tag '%s': %s", tag, e)


def revalidate_after_commit(tags):
    """Run Next.js cache invalidation only after the DB transaction commits."""
    transaction.on_commit(lambda: revalidate_nextjs(tags))


# Product signals
from .models import Product, Category, Subcategory, ProductVariant, ProductImage, InstagramPost, HeroSlider  # noqa: E402


@receiver([post_save, post_delete], sender=Product)
@receiver([post_save, post_delete], sender=ProductVariant)
@receiver([post_save, post_delete], sender=ProductImage)
def product_changed(sender, instance, **kwargs):
    """Purge homepage product sections when any product data changes."""
    revalidate_after_commit(['products'])


@receiver([post_save, post_delete], sender=Category)
@receiver([post_save, post_delete], sender=Subcategory)
def category_changed(sender, instance, **kwargs):
    """Purge categories and products when navigation structure changes."""
    revalidate_after_commit(['categories', 'products'])


@receiver([post_save, post_delete], sender=InstagramPost)
def instagram_post_changed(sender, instance, **kwargs):
    """Purge the instagram gallery section."""
    revalidate_after_commit(['instagram'])


@receiver([post_save, post_delete], sender=HeroSlider)
def hero_slider_changed(sender, instance, **kwargs):
    """Purge the hero slider section."""
    revalidate_after_commit(['hero'])
