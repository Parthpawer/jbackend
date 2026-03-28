from django.urls import path
from . import views

urlpatterns = [
    path('', views.CategoryListView.as_view(), name='category-list'),
    path('<slug:slug>/products/', views.CategoryProductsView.as_view(), name='category-products'),
    path('<slug:slug>/subcategories/', views.CategorySubcategoriesView.as_view(), name='category-subcategories'),
]
