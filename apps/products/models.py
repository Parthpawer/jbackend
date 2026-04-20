import uuid
from django.db import models


class Category(models.Model):
    """Top-level product category (e.g. Rings, Necklaces, Bangles)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    @property
    def image_url(self):
        return self.image.url if self.image else ''


class Subcategory(models.Model):
    """Subcategory under a top-level category."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='subcategories/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subcategories'
        verbose_name = 'Subcategory'
        verbose_name_plural = 'Subcategories'
        ordering = ['display_order', 'name']

    def __str__(self):
        return f'{self.category.name} → {self.name}'

    @property
    def image_url(self):
        return self.image.url if self.image else ''


class CoatingType(models.Model):
    """Database of available coating types (e.g. 18kt Yellow Gold)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="Name of the coating (e.g., 18kt Yellow Gold)")
    color_rgb = models.CharField(max_length=50, blank=True, default='#CCCCCC', help_text="Hex or RGB value (e.g., #E5A01D)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'coating_types'
        verbose_name = 'Coating Type'
        verbose_name_plural = 'Coating Types'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """A jewelry product."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    subcategory = models.ForeignKey(
        Subcategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products'
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    styling = models.TextField(blank=True, default='')
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text='Set this to override base_price with a discount')
    discount_text = models.CharField(max_length=50, blank=True, default='', help_text='e.g. "Save 20%", "Sale"')
    is_active = models.BooleanField(default=True)
    is_bestseller = models.BooleanField(default=False)
    is_quick_pick = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'is_bestseller', '-updated_at', '-created_at'], name='idx_product_bestseller'),
            models.Index(fields=['is_active', 'is_quick_pick', '-updated_at', '-created_at'], name='idx_product_quickpick'),
            models.Index(fields=['is_active', 'is_new_arrival', '-updated_at', '-created_at'], name='idx_product_newarrival'),
            models.Index(fields=['is_active', '-created_at'], name='idx_product_active_created'),
        ]

    def __str__(self):
        return self.name

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        if not img:
            img = self.images.first()
        return img.cloudinary_url if img else ''

    @property
    def min_price(self):
        variant = self.variants.order_by('price').first()
        return variant.price if variant else self.base_price

    @property
    def total_stock(self):
        return self.variants.aggregate(total=models.Sum('stock'))['total'] or 0


class ProductVariant(models.Model):
    """Variant of a product (different metal, size, etc.)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    coating = models.ForeignKey(CoatingType, on_delete=models.SET_NULL, null=True, blank=True, related_name='variants')
    metal_type = models.CharField(max_length=100, help_text='e.g. 18k Rose Gold, 22k Gold')
    size = models.CharField(max_length=50, blank=True, default='', help_text='Ring size, bangle diameter, etc.')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=0)
    sku = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_variants'
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'

    def __str__(self):
        parts = [self.metal_type]
        if self.size:
            parts.append(f'Size {self.size}')
        return f'{self.product.name} — {", ".join(parts)}'

    def save(self, *args, **kwargs):
        import logging
        logger = logging.getLogger('apps.products')
        super().save(*args, **kwargs)
        if self.stock < 5:
            logger.warning(
                f'LOW STOCK ALERT: {self.product.name} ({self.sku}) — only {self.stock} left'
            )


class ProductImage(models.Model):
    """Image for a product, stored on Cloudinary."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def cloudinary_url(self):
        return self.image.url if self.image else ''

    class Meta:
        db_table = 'product_images'
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['display_order']

    def __str__(self):
        return f"{self.product.name} Image"


class HeroSlider(models.Model):
    """Dynamic hero images for the homepage."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to='hero_sliders/')
    mobile_image = models.ImageField(
        upload_to='hero_sliders/mobile/',
        null=True,
        blank=True,
        help_text='Optional mobile-optimized hero image (recommended portrait ratio like 3:4).',
    )
    title = models.CharField(max_length=255, blank=True, default='')
    subtitle = models.CharField(max_length=255, blank=True, default='')
    link_url = models.CharField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hero_sliders'
        verbose_name = 'Hero Slider'
        verbose_name_plural = 'Hero Sliders'
        ordering = ['display_order']

    def __str__(self):
        return self.title or f"Slider {self.display_order}"

    @property
    def cloudinary_url(self):
        return self.image.url if self.image else ''

    @property
    def mobile_cloudinary_url(self):
        # Fallback to desktop image when a mobile-specific asset is not set.
        if self.mobile_image:
            return self.mobile_image.url
        return self.cloudinary_url


class InstagramPost(models.Model):
    """Instagram gallery images for the homepage."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to='instagram_gallery/')
    link_url = models.CharField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'instagram_posts'
        verbose_name = 'Instagram Post'
        verbose_name_plural = 'Instagram Posts'
        ordering = ['display_order']

    def __str__(self):
        return f"Instagram Post {self.display_order}"

    @property
    def cloudinary_url(self):
        return self.image.url if self.image else ''


# Load signals to ensure Next.js cache is purged on save
import apps.products.signals
