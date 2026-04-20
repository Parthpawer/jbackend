from django.db.models import Min, OuterRef, Subquery, CharField, Prefetch
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Category, Subcategory, Product, ProductImage, HeroSlider, InstagramPost
from .serializers import (
    CategorySerializer,
    SubcategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    HeroSliderSerializer,
    InstagramPostSerializer,
)
from .filters import ProductFilter


def api_response(data=None, message='Success', success=True, status_code=status.HTTP_200_OK):
    return Response({
        'success': success,
        'data': data,
        'message': message,
    }, status=status_code)


def annotate_product_list(queryset):
    """
    Annotate a product queryset with:
      - annotated_primary_image: URL of the primary (or first) image — zero extra queries
      - annotated_min_price: cheapest variant price
    Replaces N+1 property lookups in ProductListSerializer.
    """
    # Primary image subquery: prefer is_primary=True, fallback handled in serializer
    primary_img_sq = ProductImage.objects.filter(
        product=OuterRef('pk'), is_primary=True
    ).order_by('display_order').values('image')[:1]

    first_img_sq = ProductImage.objects.filter(
        product=OuterRef('pk')
    ).order_by('display_order').values('image')[:1]

    from django.db.models.functions import Coalesce
    from django.db.models import F

    # Min variant price subquery
    from apps.products.models import ProductVariant
    min_price_sq = ProductVariant.objects.filter(
        product=OuterRef('pk')
    ).order_by('price').values('price')[:1]

    return queryset.annotate(
        annotated_min_price=Subquery(min_price_sq),
    ).prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.order_by('display_order')),
    )


class ProductListView(generics.ListAPIView):
    """GET /api/products/ — List products with filters and search."""
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['base_price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related('category', 'subcategory')
        return annotate_product_list(qs)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
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
        ).prefetch_related(
            Prefetch('variants'),
            Prefetch('images', queryset=ProductImage.objects.order_by('display_order')),
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(serializer.data, 'Product retrieved')


@method_decorator(cache_page(60 * 15), name='dispatch')
class CategoryListView(generics.ListAPIView):
    """GET /api/categories/ — All active categories with subcategories. Cached 15 min."""
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    pagination_class = None  # Categories are a small, fully-rendered nav list

    def get_queryset(self):
        return Category.objects.filter(is_active=True).prefetch_related(
            Prefetch('subcategories', queryset=Subcategory.objects.filter(is_active=True).order_by('display_order')),
            'products',
        ).order_by('display_order')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'success': True,
            'data': response.data,
            'message': 'Categories retrieved',
        })


class CategoryProductsView(generics.ListAPIView):
    """GET /api/categories/{slug}/products/ — Products in a category (paginated)."""
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['base_price', 'created_at', 'name']
    ordering = ['-created_at']
    # Pagination inherited from global DRF settings (PAGE_SIZE=12)

    def get_queryset(self):
        slug = self.kwargs['slug']
        qs = Product.objects.filter(
            category__slug=slug, is_active=True
        ).select_related('category', 'subcategory')
        return annotate_product_list(qs)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'success': True,
            'data': response.data,
            'message': 'Category products retrieved',
        })


class CategorySubcategoriesView(generics.ListAPIView):
    """GET /api/categories/{slug}/subcategories/ — Subcategories under a category."""
    permission_classes = [AllowAny]
    serializer_class = SubcategorySerializer
    pagination_class = None

    def get_queryset(self):
        slug = self.kwargs['slug']
        category = get_object_or_404(Category, slug=slug, is_active=True)
        return Subcategory.objects.filter(category=category, is_active=True).prefetch_related('products')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'success': True,
            'data': response.data,
            'message': 'Subcategories retrieved',
        })


class SubcategoryProductsView(generics.ListAPIView):
    """GET /api/subcategories/{slug}/products/ — Products in a subcategory (paginated)."""
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['base_price', 'created_at', 'name']
    ordering = ['-created_at']
    # Pagination inherited from global DRF settings (PAGE_SIZE=12)

    def get_queryset(self):
        slug = self.kwargs['slug']
        qs = Product.objects.filter(
            subcategory__slug=slug, is_active=True
        ).select_related('category', 'subcategory')
        return annotate_product_list(qs)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'success': True,
            'data': response.data,
            'message': 'Subcategory products retrieved',
        })


class HeroSliderListView(generics.ListAPIView):
    """GET /api/products/homepage/hero/ — Active hero sliders."""
    permission_classes = [AllowAny]
    serializer_class = HeroSliderSerializer
    pagination_class = None

    def get_queryset(self):
        return HeroSlider.objects.filter(is_active=True).order_by('display_order')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return api_response(response.data, 'Hero sliders retrieved')


class InstagramPostListView(generics.ListAPIView):
    """GET /api/products/homepage/instagram/ — Active instagram posts."""
    permission_classes = [AllowAny]
    serializer_class = InstagramPostSerializer
    pagination_class = None

    def get_queryset(self):
        return InstagramPost.objects.filter(is_active=True).order_by('display_order')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return api_response(response.data, 'Instagram posts retrieved')


class BestSellerListView(generics.ListAPIView):
    """GET /api/products/homepage/bestsellers/ — Top 5 best selling products."""
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Product.objects.filter(
            is_active=True,
            is_bestseller=True
        ).select_related('category', 'subcategory').order_by('-updated_at', '-created_at')
        return annotate_product_list(qs)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return api_response(response.data, 'Best sellers retrieved')


class QuickPicksListView(generics.ListAPIView):
    """GET /api/products/homepage/quick-picks/ — Top 5 quick picks products."""
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Product.objects.filter(
            is_active=True,
            is_quick_pick=True
        ).select_related('category', 'subcategory').order_by('-updated_at', '-created_at')
        return annotate_product_list(qs)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return api_response(response.data, 'Quick picks retrieved')


class NewArrivalsListView(generics.ListAPIView):
    """GET /api/products/homepage/new-arrivals/ — Admin-curated new arrival products."""
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Product.objects.filter(
            is_active=True,
            is_new_arrival=True
        ).select_related('category', 'subcategory').order_by('-updated_at', '-created_at')
        return annotate_product_list(qs)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return api_response(response.data, 'New arrivals retrieved')


class HomepageDataView(APIView):
    """
    GET /api/products/homepage/all/ — Single aggregated endpoint for the homepage.
    Returns hero sliders, bestsellers, quick picks, new arrivals, and instagram posts
    in one shot, replacing 5 separate round-trips from Next.js.
    """
    permission_classes = [AllowAny]

    def _get_products(self, filter_kwargs, limit=5):
        qs = Product.objects.filter(
            is_active=True, **filter_kwargs
        ).select_related('category', 'subcategory').order_by('-updated_at', '-created_at')[:limit]
        return annotate_product_list(qs)

    def get(self, request):
        hero_sliders = list(HeroSlider.objects.filter(is_active=True).order_by('display_order'))
        instagram_posts = list(InstagramPost.objects.filter(is_active=True).order_by('display_order'))
        bestsellers = list(self._get_products({'is_bestseller': True}))
        quick_picks = list(self._get_products({'is_quick_pick': True}))
        new_arrivals = list(self._get_products({'is_new_arrival': True}))

        return api_response({
            'hero_sliders': HeroSliderSerializer(hero_sliders, many=True).data,
            'bestsellers': ProductListSerializer(bestsellers, many=True).data,
            'quick_picks': ProductListSerializer(quick_picks, many=True).data,
            'new_arrivals': ProductListSerializer(new_arrivals, many=True).data,
            'instagram_posts': InstagramPostSerializer(instagram_posts, many=True).data,
        }, 'Homepage data retrieved')
