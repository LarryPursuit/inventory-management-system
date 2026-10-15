"""HTTP client the CLI uses to talk to the inventory API."""

import os
from typing import Any

import requests

DEFAULT_API_URL = "http://127.0.0.1:5555/api"
TIMEOUT_SECONDS = 30  # import/search wait on OpenFoodFacts, which can be slow


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class InventoryApiClient:
    def __init__(self, base_url: str | None = None, session: requests.Session | None = None) -> None:
        self.base_url = (base_url or os.environ.get("INVENTORY_API_URL") or DEFAULT_API_URL).rstrip("/")
        self.session = session or requests.Session()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def list_items(self, search: str | None = None, low_stock: int | None = None) -> list[dict]:
        params = {key: value for key, value in (("q", search), ("low_stock", low_stock)) if value is not None}
        return self._request("GET", "/inventory", params=params)

    def get_item(self, item_id: int) -> dict[str, Any]:
        return self._request("GET", f"/inventory/{item_id}")

    def create_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/inventory", json=payload)

    def update_item(self, item_id: int, changes: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", f"/inventory/{item_id}", json=changes)

    def delete_item(self, item_id: int) -> dict[str, Any]:
        return self._request("DELETE", f"/inventory/{item_id}")

    def lookup_product(self, barcode: str) -> dict[str, Any]:
        return self._request("GET", f"/external/product/{barcode}")

    def search_products(self, name: str, limit: int = 5) -> list[dict]:
        return self._request("GET", "/external/search", params={"name": name, "limit": limit})

    def import_product(self, barcode: str, price: float = 0, stock: int = 0) -> dict[str, Any]:
        payload = {"barcode": barcode, "price": price, "stock": stock}
        return self._request("POST", "/inventory/import", json=payload)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, timeout=TIMEOUT_SECONDS, **kwargs)
        except requests.ConnectionError as error:
            raise ApiError(
                f"Can't reach the inventory API at {self.base_url}. Is the server running?"
            ) from error
        except requests.RequestException as error:
            raise ApiError(f"Request to the inventory API failed: {error}") from error

        try:
            body = response.json()
        except ValueError:
            body = None

        if not response.ok:
            message = body.get("error") if isinstance(body, dict) else None
            raise ApiError(message or f"API responded with HTTP {response.status_code}", response.status_code)
        if body is None:
            raise ApiError("API returned a response that wasn't JSON", response.status_code)
        return body
