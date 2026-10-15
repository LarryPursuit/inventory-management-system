"""Helper routes: health check, search, and low-stock filtering."""


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "items": 5}


def test_search_by_query(client):
    items = client.get("/api/inventory?q=cola").get_json()
    assert [item["id"] for item in items] == [3]


def test_blank_query_returns_everything(client):
    assert len(client.get("/api/inventory?q=%20").get_json()) == 5


def test_low_stock_filter(client):
    items = client.get("/api/inventory?low_stock=12").get_json()
    assert {item["id"] for item in items} == {2, 5}


def test_search_and_low_stock_combine(client):
    items = client.get("/api/inventory?q=crisps&low_stock=0").get_json()
    assert [item["id"] for item in items] == [5]


def test_low_stock_rejects_non_integer(client):
    response = client.get("/api/inventory?low_stock=abc")
    assert response.status_code == 400


def test_unknown_route_is_json_404(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_wrong_method_is_json_405(client):
    response = client.put("/api/inventory/1", json={})
    assert response.status_code == 405
    assert "error" in response.get_json()
