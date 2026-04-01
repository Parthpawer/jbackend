from django.urls import path
from . import views

urlpatterns = [
    path('homepage/hero/', views.HeroSliderListView.as_view(), name='hero-list'),
    path('homepage/instagram/', views.InstagramPostListView.as_view(), name='instagram-list'),
    path('homepage/bestsellers/', views.BestSellerListView.as_view(), name='bestseller-list'),
    path('homepage/quick-picks/', views.QuickPicksListView.as_view(), name='quickpicks-list'),
    path('homepage/new-arrivals/', views.NewArrivalsListView.as_view(), name='new-arrivals'),
    path('', views.ProductListView.as_view(), name='product-list'),
    path('<uuid:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
]
