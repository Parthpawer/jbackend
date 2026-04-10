import logging
import requests
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings

logger = logging.getLogger(__name__)


def _clean_env_value(value):
    """Normalize env/config strings (trim spaces + accidental quotes)."""
    if value is None:
        return ''
    if not isinstance(value, str):
        return str(value)
    return value.strip().strip('"').strip("'")


def revalidate_nextjs(tags):
    """
    Calls the Next.js /api/revalidate endpoint to purge its ISR cache
    for the given tags. Called after any admin save/delete on content
    that is displayed on cached pages (homepage sections, etc.).
    """
    frontend_url = _clean_env_value(getattr(settings, 'FRONTEND_URL', ''))
    secret = _clean_env_value(getattr(settings, 'REVALIDATION_SECRET', ''))

    # Fallback: if FRONTEND_URL is missing, use the first CORS origin.
    if not frontend_url:
        cors_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', []) or []
        if cors_origins:
            frontend_url = _clean_env_value(cors_origins[0])

    if not frontend_url or not secret:
        missing = []
        if not frontend_url:
            missing.append('FRONTEND_URL')
        if not secret:
            missing.append('REVALIDATION_SECRET')
        logger.warning(
            "Next.js revalidation skipped: missing %s.",
            ", ".join(missing),
        )
        return

    if not frontend_url.startswith(('http://', 'https://')):
        frontend_url = f"https://{frontend_url}"

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
