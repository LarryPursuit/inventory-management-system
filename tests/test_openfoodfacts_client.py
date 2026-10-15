"""OpenFoodFactsClient: request shape, normalization, and error handling (HTTP mocked)."""

from unittest.mock import Mock

import pytest
import requests

from app.openfoodfacts import (
    USER_AGENT,
    ExternalAPIError,
    OpenFoodFactsClient,
    normalize_product,
)


def make_response(status=200, payload=None, bad_json=False):
    response = Mock()
    response.status_code = status
    response.ok = 200 <= status < 300
    if bad_json:
        response.json.side_effect = ValueError("not json")
    else:
        response.json.return_value = payload
    return response


def make_client(response=None, error=None):
    session = Mock()
    if error:
        session.get.side_effect = error
    else:
        session.get.side_effect = response if isinstance(response, list) else None
        session.get.return_value = response
    client = OpenFoodFactsClient(base_url="https://off.test/", session=session, retry_delay=0)
    return client, session


FOUND = {
    "code": "3017620422003",
    "status": 1,
    "status_verbose": "product found",
    "product": {
        "product_name": "Nutella",
        "brands": "Ferrero",
        "ingredients_text": "Sucre, huile de palme",
        "ingredients_text_en": "Sugar, palm oil",
        "nutriscore_grade": "E",
        "quantity": "400 g",
    },
}


class TestGetProduct:
    def test_calls_v2_endpoint_with_fields_and_user_agent(self):
        client, session = make_client(make_response(payload=FOUND))
        client.get_product("3017620422003")
        url = session.get.call_args.args[0]
        kwargs = session.get.call_args.kwargs
        assert url == "https://off.test/api/v2/product/3017620422003.json"
        assert "product_name" in kwargs["params"]["fields"]
        assert kwargs["headers"]["User-Agent"] == USER_AGENT
        assert kwargs["timeout"] > 0

    def test_normalizes_found_product(self):
        client, _ = make_client(make_response(payload=FOUND))
        result = client.get_product("3017620422003")
        assert result == {
            "barcode": "3017620422003",
            "product": {
                "product_name": "Nutella",
                "brands": "Ferrero",
                "ingredients_text": "Sugar, palm oil",
                "quantity": "400 g",
                "nutriscore_grade": "e",
            },
        }

    def test_status_zero_means_not_found(self):
        payload = {"code": "12345678", "status": 0, "status_verbose": "product not found"}
        client, _ = make_client(make_response(payload=payload))
        assert client.get_product("12345678") is None

    def test_http_404_means_not_found(self):
        client, _ = make_client(make_response(status=404, payload={"status": 0}))
        assert client.get_product("12345678") is None

    def test_server_error_raises_after_retries(self):
        client, session = make_client(make_response(status=503))
        with pytest.raises(ExternalAPIError, match="503"):
            client.get_product("12345678")
        assert session.get.call_count == 3

    def test_retries_transient_error_then_succeeds(self):
        client, session = make_client([make_response(status=503), make_response(payload=FOUND)])
        assert client.get_product("3017620422003")["product"]["product_name"] == "Nutella"
        assert session.get.call_count == 2

    def test_client_errors_are_not_retried(self):
        client, session = make_client(make_response(status=400))
        with pytest.raises(ExternalAPIError, match="400"):
            client.get_product("12345678")
        assert session.get.call_count == 1

    def test_network_error_raises(self):
        client, _ = make_client(error=requests.ConnectionError("down"))
        with pytest.raises(ExternalAPIError, match="Could not reach"):
            client.get_product("12345678")

    def test_invalid_json_raises(self):
        client, _ = make_client(make_response(bad_json=True))
        with pytest.raises(ExternalAPIError, match="invalid JSON"):
            client.get_product("12345678")


class TestSearch:
    def test_calls_search_endpoint(self):
        client, session = make_client(make_response(payload={"products": []}))
        client.search("almond milk", limit=3)
        url = session.get.call_args.args[0]
        params = session.get.call_args.kwargs["params"]
        assert url == "https://off.test/cgi/search.pl"
        assert params["search_terms"] == "almond milk"
        assert params["json"] == 1
        assert params["page_size"] == 3

    def test_returns_normalized_results_and_skips_entries_without_code(self):
        payload = {
            "products": [
                {"code": "4056489346357", "product_name": "Almond drink", "brands": "Vemondo"},
                {"product_name": "No barcode"},
                "garbage",
            ]
        }
        client, _ = make_client(make_response(payload=payload))
        assert client.search("almond") == [
            {
                "barcode": "4056489346357",
                "product": {"product_name": "Almond drink", "brands": "Vemondo"},
            }
        ]

    def test_limit_is_clamped(self):
        client, session = make_client(make_response(payload={"products": []}))
        client.search("x", limit=500)
        assert session.get.call_args.kwargs["params"]["page_size"] == 20
        client.search("x", limit=0)
        assert session.get.call_args.kwargs["params"]["page_size"] == 1

    def test_unexpected_shape_raises(self):
        client, _ = make_client(make_response(payload={"oops": True}))
        with pytest.raises(ExternalAPIError, match="unexpected"):
            client.search("x")


class TestNormalizeProduct:
    def test_prefers_english_name(self):
        raw = {"product_name": "Lait d'amande", "product_name_en": "Almond milk"}
        assert normalize_product("1", raw)["product"]["product_name"] == "Almond milk"

    def test_drops_unknown_nutriscore_and_blank_fields(self):
        raw = {"product_name": "Water", "nutriscore_grade": "not-applicable", "brands": "  "}
        assert normalize_product("1", raw)["product"] == {"product_name": "Water"}

    def test_missing_name_gets_placeholder(self):
        assert normalize_product(123, {})["product"]["product_name"] == "Unnamed product"
        assert normalize_product(123, {})["barcode"] == "123"
