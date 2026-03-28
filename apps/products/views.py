from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from .models import Category, Subcategory, Product
from .serializers import (
    CategorySerializer,
    SubcategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
)
from .filters import ProductFilter


def api_response(data=None, message='Success', success=True, status_code=status.HTTP_200_OK):
    return Response({
        'success': success,
        'data': data,
        'message': message,
    }, status=status_code)


class ProductListView(generics.ListAPIView):
    """GET /api/products/ — List products with filters and search."""
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['base_price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related('category', 'subcategory')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        # --- DEBUG LOGGING ADDED FOR USER ---
        print("\n" + "="*50)
        print("🔍 DEBUG: Next.js is requesting Products list")
        for product in response.data.get('results', []):
            name = product.get('name', '')
            img_url = product.get('primary_image', '')
            print(f"[{name}] Image URL -> {img_url}")
            if img_url and not any(img_url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                print("   ⚠️ WARNING: This URL does NOT have a valid image extension (.jpg/.png/etc).")
                print("   Next.js Image Optimizer WILL NOT render it! Please re-upload with an extension.")
        print("="*50 + "\n")
        
        return Response({
            'success': True,
            'data': response.data,
            'message': 'Products retrieved',
        })


class ProductDetailView(generics.RetrieveAPIView):
    """GET /api/products/{id}/ — Product detail with variants and images."""
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related(
            'category', 'subcategory'
        ).prefetch_related('variants', 'images')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(serializer.data, 'Product retrieved')


class CategoryListView(generics.ListAPIView):
    """GET /api/categories/ — All active categories with subcategories."""
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(is_active=True).prefetch_related(
            'subcategories'
        ).order_by('display_order')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'success': True,
            'data': response.data,
            'message': 'Categories retrieved',
        })


class CategoryProductsView(generics.ListAPIView):
    """GET /api/categories/{slug}/products/ — Products in a category."""
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        slug = self.kwargs['slug']
        return Product.objects.filter(
            category__slug=slug, is_active=True
        ).select_related('category', 'subcategory')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        # --- DEBUG LOGGING ---
        print("\n" + "="*50)
        print(f"🔍 DEBUG: Next.js is requesting products for category")
        for product in response.data.get('results', []):
            name = product.get('name', '')
            img_url = product.get('primary_image', '')
            print(f"[{name}] Image URL -> {img_url}")
            if img_url and not any(img_url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                print("   ⚠️ WARNING: This URL does NOT have a valid image extension (.jpg/.png/etc).")
                print("   Next.js WILL NOT render it! Please re-upload with an extension.")
        print("="*50 + "\n")

        return Response({
            'success': True,
            'data': response.data,
            'message': 'Category products retrieved',
        })


class CategorySubcategoriesView(generics.ListAPIView):
    """GET /api/categories/{slug}/subcategories/ — Subcategories under a category."""
    permission_classes = [AllowAny]
    serializer_class = SubcategorySerializer

    def get_queryset(self):
        slug = self.kwargs['slug']
        category = get_object_or_404(Category, slug=slug, is_active=True)
        return Subcategory.objects.filter(category=category, is_active=True)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'success': True,
            'data': response.data,
            'message': 'Subcategories retrieved',
        })


class SubcategoryProductsView(generics.ListAPIView):
    """GET /api/subcategories/{slug}/products/ — Products in a subcategory."""
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        slug = self.kwargs['slug']
        return Product.objects.filter(
            subcategory__slug=slug, is_active=True
        ).select_related('category', 'subcategory')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'success': True,
            'data': response.data,
            'message': 'Subcategory products retrieved',
        })
