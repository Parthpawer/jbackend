import django_filters
from .models import Product


class ProductFilter(django_filters.FilterSet):
    """Filters for product list view."""

    category = django_filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    subcategory = django_filters.CharFilter(field_name='subcategory__slug', lookup_expr='exact')
    metal_type = django_filters.CharFilter(field_name='variants__metal_type', lookup_expr='icontains')
    price_min = django_filters.NumberFilter(field_name='base_price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='base_price', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Product
        fields = ['category', 'subcategory', 'metal_type', 'price_min', 'price_max']

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            models.Q(name__icontains=value) |
            models.Q(description__icontains=value) |
            models.Q(variants__metal_type__icontains=value)
        ).distinct()


# Fix import for Q objects
from django.db import models  # noqa: E402
