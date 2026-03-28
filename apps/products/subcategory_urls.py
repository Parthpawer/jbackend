from django.urls import path
from . import views

urlpatterns = [
    path('<slug:slug>/products/', views.SubcategoryProductsView.as_view(), name='subcategory-products'),
]
