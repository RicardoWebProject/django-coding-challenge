from django.urls import path

from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    # Products
    path("api/products/", views.ProductListCreateView.as_view(), name="product-list-create"),
    path("api/products/<int:pk>/", views.ProductDetailView.as_view(), name="product-detail"),
    # Orders
    path("api/orders/", views.OrderListCreateView.as_view(), name="order-list-create"),
    path("api/orders/<int:pk>/", views.OrderDetailView.as_view(), name="order-detail"),
    path("api/orders/<int:pk>/cancel/", views.OrderCancelView.as_view(), name="order-cancel"),
    path("api/orders/<int:pk>/fulfill/", views.OrderFulfillView.as_view(), name="order-fulfill"),
]
