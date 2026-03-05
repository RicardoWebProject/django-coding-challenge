from django.db import transaction
from django.views import generic
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order, Product
from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    ProductSerializer,
)


class IndexView(generic.TemplateView):
    template_name = "index.html"


# ---------------------------------------------------------------------------
# Product endpoints
# ---------------------------------------------------------------------------

class ProductListCreateView(generics.ListCreateAPIView):
    """GET /api/products/  —  POST /api/products/"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class ProductDetailView(generics.RetrieveUpdateAPIView):
    """GET /api/products/<pk>/  —  PUT/PATCH /api/products/<pk>/"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


# ---------------------------------------------------------------------------
# Order endpoints
# ---------------------------------------------------------------------------

class OrderListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/orders/  — list all orders (with items)
    POST /api/orders/  — place a new order
    """
    queryset = Order.objects.prefetch_related("items__product").order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OrderCreateSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        response_serializer = OrderSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    """GET /api/orders/<pk>/"""
    queryset = Order.objects.prefetch_related("items__product")
    serializer_class = OrderSerializer


class OrderFulfillView(APIView):
    """POST /api/orders/<pk>/fulfill/"""

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.status != Order.Status.PENDING:
            return Response(
                {"detail": f"Cannot fulfill an order with status '{order.status}'. Only pending orders can be fulfilled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = Order.Status.FULFILLED
        order.save(update_fields=["status", "updated_at"])

        return Response(OrderSerializer(order).data)


class OrderCancelView(APIView):
    """POST /api/orders/<pk>/cancel/"""

    def post(self, request, pk):
        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(pk=pk)
            except Order.DoesNotExist:
                return Response(
                    {"detail": "Order not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if order.status != Order.Status.PENDING:
                return Response(
                    {"detail": f"Cannot cancel an order with status '{order.status}'. Only pending orders can be cancelled."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Restore stock for every item in the order
            for item in order.items.select_related("product"):
                product = Product.objects.select_for_update().get(pk=item.product_id)
                product.stock_quantity += item.quantity
                product.save(update_fields=["stock_quantity"])

            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status", "updated_at"])

        return Response(OrderSerializer(order).data)

