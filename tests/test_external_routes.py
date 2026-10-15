"""External API routes: lookup, search, and import into the inventory."""

import pytest

from app import create_app
from tests.conftest import ALMOND_MILK, FakeFoodClient


@pytest.fixture
def failing_client():
    return create_app(food_client=FakeFoodClient(fail=True)).test_client()


class TestLookup:
    def test_returns_product_without_saving_it(self, client):
        response = client.get(f"/api/external/product/{ALMOND_MILK['barcode']}")
        assert response.status_code == 200
        assert response.get_json() == ALMOND_MILK
        assert len(client.get("/api/inventory").get_json()) == 5

    def test_unknown_barcode_is_404(self, client):
        assert client.get("/api/external/product/99999999").status_code == 404

    def test_invalid_barcode_is_400_and_skips_api(self, client, food_client):
        assert client.get("/api/external/product/abc").status_code == 400
        assert food_client.calls == []

    def test_upstream_failure_is_502(self, failing_client):
        response = failing_client.get("/api/external/product/12345678")
        assert response.status_code == 502
        assert "unavailable" in response.get_json()["error"]


class TestSearch:
    def test_search_by_name(self, client, food_client):
        response = client.get("/api/external/search?name=almond&limit=3")
        assert response.status_code == 200
        assert response.get_json() == [ALMOND_MILK]
        assert food_client.calls == [("search", "almond", 3)]

    def test_default_limit(self, client, food_client):
        client.get("/api/external/search?name=milk")
        assert food_client.calls == [("search", "milk", 5)]

    @pytest.mark.parametrize("query", ["", "?name=", "?name=%20%20"])
    def test_name_required(self, client, query):
        assert client.get(f"/api/external/search{query}").status_code == 400

    @pytest.mark.parametrize("limit", ["0", "21", "abc", "-1"])
    def test_limit_must_be_in_range(self, client, limit):
        assert client.get(f"/api/external/search?name=x&limit={limit}").status_code == 400

    def test_upstream_failure_is_502(self, failing_client):
        assert failing_client.get("/api/external/search?name=x").status_code == 502


class TestImport:
    def test_imports_product_into_inventory(self, client):
        response = client.post(
            "/api/inventory/import",
            json={"barcode": ALMOND_MILK["barcode"], "price": 3.99, "stock": 12},
        )
        assert response.status_code == 201
        item = response.get_json()
        assert item["id"] == 6
        assert item["product"] == ALMOND_MILK["product"]
        assert (item["price"], item["stock"]) == (3.99, 12)
        assert client.get("/api/inventory/6").get_json() == item

    def test_defaults_price_and_stock_to_zero(self, client):
        item = client.post("/api/inventory/import", json={"barcode": ALMOND_MILK["barcode"]}).get_json()
        assert (item["price"], item["stock"]) == (0.0, 0)

    def test_existing_barcode_is_409_and_skips_api(self, client, food_client):
        response = client.post("/api/inventory/import", json={"barcode": "3017620422003"})
        assert response.status_code == 409
        assert food_client.calls == []

    def test_unknown_product_is_404(self, client):
        response = client.post("/api/inventory/import", json={"barcode": "99999999"})
        assert response.status_code == 404
        assert len(client.get("/api/inventory").get_json()) == 5

    def test_invalid_body_is_400(self, client):
        assert client.post("/api/inventory/import", json={"stock": 2}).status_code == 400
        assert client.post("/api/inventory/import", json={"barcode": "1"}).status_code == 400

    def test_upstream_failure_is_502(self, failing_client):
        response = failing_client.post("/api/inventory/import", json={"barcode": "12345678"})
        assert response.status_code == 502
