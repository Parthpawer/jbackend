from rest_framework import serializers
from .models import Category, Subcategory, Product, ProductVariant, ProductImage, HeroSlider, InstagramPost


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'cloudinary_url', 'is_primary', 'display_order')


class ProductVariantSerializer(serializers.ModelSerializer):
    low_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ('id', 'metal_type', 'size', 'price', 'stock', 'sku', 'low_stock')

    def get_low_stock(self, obj):
        return obj.stock < 5


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product listings."""
    primary_image = serializers.CharField(read_only=True)
    min_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, default=None)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'base_price', 'min_price', 'primary_image',
            'category_name', 'subcategory_name', 'is_bestseller', 'created_at'
        )


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full serializer for product detail page."""
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, default=None)
    subcategory_slug = serializers.CharField(source='subcategory.slug', read_only=True, default=None)
    total_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'description', 'base_price', 'is_active', 'is_bestseller',
            'category', 'category_name', 'category_slug',
            'subcategory', 'subcategory_name', 'subcategory_slug',
            'images', 'variants', 'total_stock', 'created_at'
        )


class SubcategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Subcategory
        fields = ('id', 'name', 'slug', 'image_url', 'display_order', 'product_count')

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubcategorySerializer(many=True, read_only=True)
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'image_url', 'display_order', 'subcategories', 'product_count')

    def get_product_count(self, obj):
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
