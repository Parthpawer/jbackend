from django.urls import path
from . import views

urlpatterns = [
    path('', views.CartView.as_view(), name='cart'),
    path('items/', views.CartItemAddView.as_view(), name='cart-add-item'),
    path('items/<uuid:pk>/', views.CartItemUpdateView.as_view(), name='cart-update-item'),
    path('items/<uuid:pk>/delete/', views.CartItemDeleteView.as_view(), name='cart-delete-item'),
    path('clear/', views.CartClearView.as_view(), name='cart-clear'),
]
