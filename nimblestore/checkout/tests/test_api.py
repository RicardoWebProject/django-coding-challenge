import pytest
from rest_framework.test import APIClient

from checkout.models import Order, OrderItem, Product


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def product(db):
    """A single product with enough stock for most tests."""
    return Product.objects.create(name="Laptop", price="999.99", stock_quantity=10)


@pytest.fixture
def low_stock_product(db):
    """A product with only 1 unit in stock."""
    return Product.objects.create(name="Last Unit", price="50.00", stock_quantity=1)


@pytest.fixture
def placed_order(db, product):
    """A pending order with 2 units of `product`."""
    order = Order.objects.create()
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=2,
        unit_price=product.price,
    )
    product.stock_quantity -= 2
    product.save()
    return order


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProducts:
    def test_list_products(self, api_client, product):
        response = api_client.get("/api/products/")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Laptop"

    def test_create_product(self, api_client, db):
        payload = {"name": "Mouse", "price": "25.00", "stock_quantity": 100}
        response = api_client.post("/api/products/", payload, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "Mouse"
        assert Product.objects.count() == 1

    def test_update_product_price(self, api_client, product):
        response = api_client.patch(
            f"/api/products/{product.id}/",
            {"price": "1199.99"},
            format="json",
        )
        assert response.status_code == 200
        product.refresh_from_db()
        assert float(product.price) == 1199.99

    def test_update_product_stock(self, api_client, product):
        response = api_client.patch(
            f"/api/products/{product.id}/",
            {"stock_quantity": 50},
            format="json",
        )
        assert response.status_code == 200
        product.refresh_from_db()
        assert product.stock_quantity == 50


# ---------------------------------------------------------------------------
# Order creation — happy path & validation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestOrderCreation:
    def test_place_order_happy_path(self, api_client, product):
        payload = {"items": [{"product": product.id, "quantity": 3}]}
        response = api_client.post("/api/orders/", payload, format="json")
        assert response.status_code == 201
        assert response.data["status"] == "pending"
        assert len(response.data["items"]) == 1

    def test_place_order_deducts_stock(self, api_client, product):
        api_client.post(
            "/api/orders/",
            {"items": [{"product": product.id, "quantity": 4}]},
            format="json",
        )
        product.refresh_from_db()
        assert product.stock_quantity == 6  # 10 - 4

    def test_place_order_locks_price(self, api_client, product):
        """Unit price recorded at order time must not change when the product price changes."""
        response = api_client.post(
            "/api/orders/",
            {"items": [{"product": product.id, "quantity": 1}]},
            format="json",
        )
        order_item = response.data["items"][0]
        assert float(order_item["unit_price"]) == float(product.price)

        # Change the product price after the order was placed
        api_client.patch(f"/api/products/{product.id}/", {"price": "1.00"}, format="json")

        # Re-fetch the order and verify the locked price is unchanged
        order_id = response.data["id"]
        detail = api_client.get(f"/api/orders/{order_id}/")
        assert float(detail.data["items"][0]["unit_price"]) == 999.99

    def test_reject_order_when_insufficient_stock(self, api_client, product):
        payload = {"items": [{"product": product.id, "quantity": 99}]}
        response = api_client.post("/api/orders/", payload, format="json")
        assert response.status_code == 400

    def test_reject_order_when_out_of_stock(self, api_client, low_stock_product):
        # Buy the last unit first
        api_client.post(
            "/api/orders/",
            {"items": [{"product": low_stock_product.id, "quantity": 1}]},
            format="json",
        )
        # Second attempt must be rejected
        response = api_client.post(
            "/api/orders/",
            {"items": [{"product": low_stock_product.id, "quantity": 1}]},
            format="json",
        )
        assert response.status_code == 400

    def test_reject_empty_order(self, api_client, db):
        response = api_client.post("/api/orders/", {"items": []}, format="json")
        assert response.status_code == 400

    def test_reject_duplicate_products_in_order(self, api_client, product):
        payload = {
            "items": [
                {"product": product.id, "quantity": 1},
                {"product": product.id, "quantity": 2},
            ]
        }
        response = api_client.post("/api/orders/", payload, format="json")
        assert response.status_code == 400

    def test_failed_order_does_not_deduct_stock(self, api_client, product):
        """A rejected order must leave stock untouched."""
        before = product.stock_quantity
        api_client.post(
            "/api/orders/",
            {"items": [{"product": product.id, "quantity": 999}]},
            format="json",
        )
        product.refresh_from_db()
        assert product.stock_quantity == before


# ---------------------------------------------------------------------------
# Order listing & detail
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestOrderRetrieval:
    def test_list_orders(self, api_client, placed_order):
        response = api_client.get("/api/orders/")
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_order_detail(self, api_client, placed_order):
        response = api_client.get(f"/api/orders/{placed_order.id}/")
        assert response.status_code == 200
        assert response.data["id"] == placed_order.id
        assert len(response.data["items"]) == 1

    def test_order_detail_not_found(self, api_client, db):
        response = api_client.get("/api/orders/9999/")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Order cancellation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestOrderCancellation:
    def test_cancel_pending_order(self, api_client, placed_order, product):
        response = api_client.post(f"/api/orders/{placed_order.id}/cancel/")
        assert response.status_code == 200
        placed_order.refresh_from_db()
        assert placed_order.status == Order.Status.CANCELLED

    def test_cancel_restores_stock(self, api_client, placed_order, product):
        stock_before_cancel = product.stock_quantity  # 8 after order placed by fixture
        api_client.post(f"/api/orders/{placed_order.id}/cancel/")
        product.refresh_from_db()
        assert product.stock_quantity == stock_before_cancel + 2

    def test_cannot_cancel_fulfilled_order(self, api_client, placed_order):
        placed_order.status = Order.Status.FULFILLED
        placed_order.save()
        response = api_client.post(f"/api/orders/{placed_order.id}/cancel/")
        assert response.status_code == 400

    def test_cannot_cancel_already_cancelled_order(self, api_client, placed_order):
        api_client.post(f"/api/orders/{placed_order.id}/cancel/")
        response = api_client.post(f"/api/orders/{placed_order.id}/cancel/")
        assert response.status_code == 400

    def test_cancel_nonexistent_order(self, api_client, db):
        response = api_client.post("/api/orders/9999/cancel/")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Order fulfillment
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestOrderFulfillment:
    def test_fulfill_pending_order(self, api_client, placed_order):
        response = api_client.post(f"/api/orders/{placed_order.id}/fulfill/")
        assert response.status_code == 200
        placed_order.refresh_from_db()
        assert placed_order.status == Order.Status.FULFILLED

    def test_cannot_fulfill_cancelled_order(self, api_client, placed_order):
        placed_order.status = Order.Status.CANCELLED
        placed_order.save()
        response = api_client.post(f"/api/orders/{placed_order.id}/fulfill/")
        assert response.status_code == 400

    def test_cannot_fulfill_already_fulfilled_order(self, api_client, placed_order):
        api_client.post(f"/api/orders/{placed_order.id}/fulfill/")
        response = api_client.post(f"/api/orders/{placed_order.id}/fulfill/")
        assert response.status_code == 400

    def test_fulfill_nonexistent_order(self, api_client, db):
        response = api_client.post("/api/orders/9999/fulfill/")
        assert response.status_code == 404

