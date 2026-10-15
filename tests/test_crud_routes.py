"""CRUD routes: GET list/one, POST, PATCH, DELETE."""


class TestRead:
    def test_list_returns_all_seed_items(self, client):
        response = client.get("/api/inventory")
        assert response.status_code == 200
        items = response.get_json()
        assert len(items) == 5
        assert items[0]["product"]["product_name"] == "Organic Soymilk"

    def test_get_one(self, client):
        response = client.get("/api/inventory/2")
        assert response.status_code == 200
        assert response.get_json()["barcode"] == "3017620422003"

    def test_get_missing_returns_json_404(self, client):
        response = client.get("/api/inventory/999")
        assert response.status_code == 404
        assert response.get_json() == {"error": "Item 999 not found"}


class TestCreate:
    def test_creates_item_with_new_id(self, client, new_item):
        response = client.post("/api/inventory", json=new_item)
        assert response.status_code == 201
        created = response.get_json()
        assert created["id"] == 6
        assert created["product"]["nutriscore_grade"] == "d"
        assert client.get("/api/inventory/6").get_json() == created

    def test_rejects_missing_fields(self, client):
        response = client.post("/api/inventory", json={"barcode": "12345678"})
        assert response.status_code == 400
        error = response.get_json()["error"]
        assert "'product' is required" in error
        assert "'price' is required" in error

    def test_rejects_missing_product_name(self, client, new_item):
        payload = {**new_item, "product": {"brands": "Lay's"}}
        response = client.post("/api/inventory", json=payload)
        assert response.status_code == 400
        assert "product_name" in response.get_json()["error"]

    def test_rejects_non_json_body(self, client):
        response = client.post("/api/inventory", data="hello", content_type="text/plain")
        assert response.status_code == 400

    def test_rejects_duplicate_barcode(self, client, new_item):
        payload = {**new_item, "barcode": "3017620422003"}
        response = client.post("/api/inventory", json=payload)
        assert response.status_code == 409

    def test_rejects_client_supplied_id(self, client, new_item):
        response = client.post("/api/inventory", json={**new_item, "id": 42})
        assert response.status_code == 400
        assert "id" in response.get_json()["error"]


class TestUpdate:
    def test_patch_updates_only_given_fields(self, client):
        response = client.patch(
            "/api/inventory/1", json={"stock": 3, "product": {"brands": "Silk Inc"}}
        )
        assert response.status_code == 200
        item = response.get_json()
        assert item["stock"] == 3
        assert item["price"] == 4.49
        assert item["product"]["brands"] == "Silk Inc"
        assert item["product"]["product_name"] == "Organic Soymilk"

    def test_patch_missing_item(self, client):
        assert client.patch("/api/inventory/999", json={"stock": 1}).status_code == 404

    def test_patch_rejects_invalid_values(self, client):
        response = client.patch("/api/inventory/1", json={"stock": -2})
        assert response.status_code == 400

    def test_patch_rejects_empty_body(self, client):
        response = client.patch("/api/inventory/1", json={})
        assert response.status_code == 400
        assert "at least one field" in response.get_json()["error"]

    def test_patch_rejects_barcode_owned_by_another_item(self, client):
        response = client.patch("/api/inventory/1", json={"barcode": "3017620422003"})
        assert response.status_code == 409

    def test_patch_allows_keeping_own_barcode(self, client):
        response = client.patch("/api/inventory/1", json={"barcode": "0025293600232"})
        assert response.status_code == 200


class TestDelete:
    def test_delete_removes_item(self, client):
        response = client.delete("/api/inventory/3")
        assert response.status_code == 200
        body = response.get_json()
        assert body["item"]["id"] == 3
        assert client.get("/api/inventory/3").status_code == 404
        assert len(client.get("/api/inventory").get_json()) == 4

    def test_delete_missing_item(self, client):
        assert client.delete("/api/inventory/999").status_code == 404


def test_each_app_gets_isolated_data(client):
    client.delete("/api/inventory/1")
    from app import create_app

    fresh = create_app().test_client()
    assert fresh.get("/api/inventory/1").status_code == 200
