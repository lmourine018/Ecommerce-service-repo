from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import path

from . import views
from mozilla_django_oidc import views as oidc_views
from .views import (
    CategoryListCreateAPIView, CategoryDetailAPIView,
    ProductListCreateAPIView, ProductDetailAPIView,
    CustomerListCreateAPIView, CustomerDetailAPIView,
    OrderListCreateAPIView, OrderDetailAPIView, OrderItemListCreateAPIView, OrderItemDetailAPIView, AveragePriceView
)
@login_required
def home(request):
    return JsonResponse({
        "username": request.user.username,
        "email": request.user.email
    })
urlpatterns = [
    path('categories/', CategoryListCreateAPIView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailAPIView.as_view(), name='category-detail'),

    path('products/', ProductListCreateAPIView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailAPIView.as_view(), name='product-detail'),

    path('customers/', CustomerListCreateAPIView.as_view(), name='customer-list'),
    path('customers/<int:pk>/', CustomerDetailAPIView.as_view(), name='customer-detail'),

    path('orders/', OrderListCreateAPIView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailAPIView.as_view(), name='order-detail'),

    path('order-item/', OrderItemListCreateAPIView.as_view(), name='order-item-list'),
    path('order-item/<int:pk>/', OrderItemDetailAPIView.as_view(), name='order-item-detail'),
    # Custom auth views
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path("oidc/authenticate/", oidc_views.OIDCAuthenticationRequestView.as_view(), name="oidc_authentication_init"),
    path("oidc/callback/", oidc_views.OIDCAuthenticationCallbackView.as_view(), name="oidc_callback"),
    # API endpoints
    path('api/customer/profile/', views.CustomerProfileAPIView.as_view(), name='api-customer-profile'),
    path('api/customer/update/', views.CustomerUpdateAPIView.as_view(), name='api-customer-update'),
    path("", home),
    path('categories/<int:category_id>/average-price/', AveragePriceView.as_view(), name='average-price'),

]
