"""InventoryApiClient: each method against the real routes, plus failure handling."""

from unittest.mock import Mock

import pytest
import requests

from inventory_cli.api_client import DEFAULT_API_URL, ApiError, InventoryApiClient
from tests.conftest import ALMOND_MILK


def test_base_url_defaults_and_env(monkeypatch):
    monkeypatch.delenv("INVENTORY_API_URL", raising=False)
    assert InventoryApiClient().base_url == DEFAULT_API_URL
    monkeypatch.setenv("INVENTORY_API_URL", "http://example.test/api/")
    assert InventoryApiClient().base_url == "http://example.test/api"
    assert InventoryApiClient("http://x/api").base_url == "http://x/api"


def test_crud_round_trip(api, new_item):
    assert api.health()["status"] == "ok"
    assert len(api.list_items()) == 5
    assert [i["id"] for i in api.list_items(search="nutella")] == [2]
    assert [i["id"] for i in api.list_items(low_stock=0)] == [5]
    created = api.create_item(new_item)
    assert api.get_item(created["id"]) == created
    assert api.update_item(created["id"], {"stock": 1})["stock"] == 1
    assert api.delete_item(created["id"])["item"]["id"] == created["id"]


def test_external_methods(api):
    assert api.lookup_product(ALMOND_MILK["barcode"]) == ALMOND_MILK
    assert api.search_products("almond", limit=2) == [ALMOND_MILK]
    item = api.import_product(ALMOND_MILK["barcode"], 2.5, 4)
    assert (item["price"], item["stock"]) == (2.5, 4)


def test_api_error_message_and_status_come_from_server(api):
    with pytest.raises(ApiError, match="Item 999 not found") as caught:
        api.get_item(999)
    assert caught.value.status == 404


def mock_session(response=None, error=None):
    session = Mock()
    session.request.side_effect = error
    session.request.return_value = response
    return InventoryApiClient("http://x/api", session=session)


def test_connection_error_explains_server_is_down():
    client = mock_session(error=requests.ConnectionError())
    with pytest.raises(ApiError, match="Is the server running"):
        client.health()


def test_other_request_errors():
    client = mock_session(error=requests.Timeout("slow"))
    with pytest.raises(ApiError, match="failed: slow"):
        client.health()


def test_error_without_json_body_reports_status():
    response = Mock(ok=False, status_code=500)
    response.json.side_effect = ValueError
    with pytest.raises(ApiError, match="HTTP 500"):
        mock_session(response).health()


def test_success_without_json_body():
    response = Mock(ok=True, status_code=200)
    response.json.side_effect = ValueError
    with pytest.raises(ApiError, match="wasn't JSON"):
        mock_session(response).health()
