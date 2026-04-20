from django.urls import path
from . import views

urlpatterns = [
    # ── Aggregated homepage endpoint (replaces 5 round-trips) ──────────────
    path('homepage/all/', views.HomepageDataView.as_view(), name='homepage-all'),
    # ── Individual homepage endpoints (kept for backwards compatibility) ────
    path('homepage/hero/', views.HeroSliderListView.as_view(), name='hero-list'),
    path('homepage/instagram/', views.InstagramPostListView.as_view(), name='instagram-list'),
    path('homepage/bestsellers/', views.BestSellerListView.as_view(), name='bestseller-list'),
    path('homepage/quick-picks/', views.QuickPicksListView.as_view(), name='quickpicks-list'),
    path('homepage/new-arrivals/', views.NewArrivalsListView.as_view(), name='new-arrivals'),
    # ── Product CRUD ────────────────────────────────────────────────────────
    path('', views.ProductListView.as_view(), name='product-list'),
    path('<uuid:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
]
