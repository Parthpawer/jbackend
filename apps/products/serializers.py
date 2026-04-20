from rest_framework import serializers
from .models import Category, Subcategory, Product, ProductVariant, ProductImage, HeroSlider, InstagramPost, CoatingType


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'cloudinary_url', 'is_primary', 'display_order')


class CoatingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoatingType
        fields = ('id', 'name', 'color_rgb')


class ProductVariantSerializer(serializers.ModelSerializer):
    low_stock = serializers.SerializerMethodField()
    coating = CoatingTypeSerializer(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ('id', 'coating', 'metal_type', 'size', 'price', 'stock', 'sku', 'low_stock')

    def get_low_stock(self, obj):
        return obj.stock < 5


class ProductListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for product listings.

    Relies on DB annotations applied by ProductQuerysetMixin.annotate_list():
      - annotated_primary_image  → URL of primary image
      - annotated_min_price      → lowest variant price
    Using annotated fields avoids N+1 queries per product.
    """
    primary_image = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, default=None)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'base_price', 'min_price', 'discounted_price', 'discount_text', 'primary_image',
            'category_name', 'subcategory_name', 'is_bestseller', 'is_quick_pick', 'is_new_arrival', 'created_at'
        )

    def get_primary_image(self, obj):
        # Prefer DB annotation (zero extra query); fall back to prefetch only if needed.
        annotated = getattr(obj, 'annotated_primary_image', None)
        if annotated is not None:
            return annotated
        # Fallback: use prefetched images cache if available
        if hasattr(obj, '_prefetched_objects_cache') and 'images' in obj._prefetched_objects_cache:
            images = obj._prefetched_objects_cache['images']
            primary = next((img for img in images if img.is_primary), None)
            img = primary or (images[0] if images else None)
            return img.cloudinary_url if img else ''
        return ''

    def get_min_price(self, obj):
        # Prefer DB annotation; else fall back to base_price
        annotated = getattr(obj, 'annotated_min_price', None)
        if annotated is not None:
            return annotated
        return obj.base_price


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full serializer for product detail page."""
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, default=None)
    subcategory_slug = serializers.CharField(source='subcategory.slug', read_only=True, default=None)
    total_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'description', 'styling', 'base_price', 'discounted_price', 'discount_text', 'is_active', 'is_bestseller', 'is_quick_pick', 'is_new_arrival',
            'category', 'category_name', 'category_slug',
            'subcategory', 'subcategory_name', 'subcategory_slug',
            'images', 'variants', 'total_stock', 'created_at'
        )

    def get_total_stock(self, obj):
        # Use prefetched variants cache to avoid extra aggregate query
        if hasattr(obj, '_prefetched_objects_cache') and 'variants' in obj._prefetched_objects_cache:
            return sum(v.stock for v in obj._prefetched_objects_cache['variants'])
        return obj.variants.aggregate(total=__import__('django.db.models', fromlist=['Sum']).Sum('stock'))['total'] or 0


class SubcategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Subcategory
        fields = ('id', 'name', 'slug', 'image_url', 'display_order', 'product_count')

    def get_product_count(self, obj):
        # Use prefetched products if available
        if hasattr(obj, '_prefetched_objects_cache') and 'products' in obj._prefetched_objects_cache:
            return sum(1 for p in obj._prefetched_objects_cache['products'] if p.is_active)
        return obj.products.filter(is_active=True).count()


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubcategorySerializer(many=True, read_only=True)
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'image_url', 'display_order', 'subcategories', 'product_count')

    def get_product_count(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'products' in obj._prefetched_objects_cache:
            return sum(1 for p in obj._prefetched_objects_cache['products'] if p.is_active)
        return obj.products.filter(is_active=True).count()


class CategoryListSerializer(serializers.ModelSerializer):
    """Lightweight category serializer without nested subcategories."""

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'image_url', 'display_order')


class HeroSliderSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroSlider
        fields = ('id', 'title', 'subtitle', 'link_url', 'cloudinary_url', 'display_order')


class InstagramPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstagramPost
        fields = ('id', 'link_url', 'cloudinary_url', 'display_order')
