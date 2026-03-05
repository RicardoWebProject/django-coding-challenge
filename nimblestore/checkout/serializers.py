from django.db import transaction
from rest_framework import serializers
from .models import Order, OrderItem, Product


# ---------------------------------------------------------------------------
# Product serializers
# ---------------------------------------------------------------------------

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "price", "stock_quantity"]


# ---------------------------------------------------------------------------
# Order read serializers
# ---------------------------------------------------------------------------

class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "product_name", "quantity", "unit_price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "status", "created_at", "updated_at", "items"]


# ---------------------------------------------------------------------------
# Order creation serializer (write)
# ---------------------------------------------------------------------------

class OrderItemInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        # Reject duplicate products — caller should combine quantities instead
        product_ids = [item["product"].id for item in value]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                "Duplicate products are not allowed. Combine quantities into a single item."
            )
        return value

    def create(self, validated_data):
        items_data = validated_data["items"]

        with transaction.atomic():
            # Lock rows in a consistent order (by pk) to prevent deadlocks
            product_ids = sorted(item["product"].id for item in items_data)
            locked_products = {
                p.id: p
                for p in Product.objects.select_for_update().filter(id__in=product_ids)
            }

            # Validate stock before touching anything
            errors = []
            for item in items_data:
                product = locked_products[item["product"].id]
                if product.stock_quantity < item["quantity"]:
                    errors.append(
                        f"Insufficient stock for '{product.name}': "
                        f"available {product.stock_quantity}, requested {item['quantity']}."
                    )
            if errors:
                raise serializers.ValidationError({"items": errors})

            # Create the order
            order = Order.objects.create()

            # Create items, lock in purchase price, deduct stock
            for item in items_data:
                product = locked_products[item["product"].id]
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item["quantity"],
                    unit_price=product.price,  # price locked at purchase time
                )
                product.stock_quantity -= item["quantity"]
                product.save(update_fields=["stock_quantity"])

        return order

