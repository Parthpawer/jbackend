from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.CreateOrderView.as_view(), name='order-create'),
    path('verify-payment/', views.VerifyPaymentView.as_view(), name='order-verify-payment'),
    path('webhook/', views.RazorpayWebhookView.as_view(), name='razorpay-webhook'),
    path('', views.OrderListView.as_view(), name='order-list'),
    path('<uuid:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('<uuid:pk>/cancel/', views.OrderCancelView.as_view(), name='order-cancel'),
    path('<uuid:pk>/payments/', views.OrderPaymentsView.as_view(), name='order-payments'),
]
