from django.contrib import admin
from .models import Category, Subcategory, Product, ProductVariant, ProductImage


class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    extra = 1
    fields = ('name', 'slug', 'image', 'is_active', 'display_order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'display_order')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SubcategoryInline]


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'slug', 'is_active', 'display_order')
    list_filter = ('is_active', 'category')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('metal_type', 'size', 'price', 'stock', 'sku')


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'is_primary', 'display_order')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'subcategory', 'base_price', 'is_active', 'total_stock', 'created_at')
    list_filter = ('is_active', 'category', 'subcategory', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [ProductVariantInline, ProductImageInline]

    fieldsets = (
        ('Product Info', {
            'fields': ('id', 'name', 'description', 'base_price')
        }),
        ('Categorization', {
            'fields': ('category', 'subcategory')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def total_stock(self, obj):
        return obj.total_stock
    total_stock.short_description = 'Total Stock'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'metal_type', 'size', 'price', 'stock', 'sku')
    list_filter = ('metal_type',)
    search_fields = ('product__name', 'sku', 'metal_type')


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_primary', 'display_order')
    list_filter = ('is_primary',)
