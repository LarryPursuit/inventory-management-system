"""Thin client for the OpenFoodFacts API.

Docs: https://openfoodfacts.github.io/openfoodfacts-server/api/

- Barcode lookup uses ``GET /api/v2/product/<barcode>.json``.
- Name search uses ``GET /cgi/search.pl`` (the v2 search endpoint has no
  full-text search, so the docs point to this one for search terms).

Both responses are normalized into ``{"barcode": ..., "product": {...}}`` with
the same ``product`` fields the inventory stores (see ``app.data``).
"""

import time
from typing import Any

import requests

from app.data import PRODUCT_FIELDS

DEFAULT_BASE_URL = "https://world.openfoodfacts.org"
# OpenFoodFacts asks every app to identify itself with a descriptive User-Agent.
USER_AGENT = "InventoryAdminLab/1.0 (Flatiron student project)"
TIMEOUT_SECONDS = 10
MAX_SEARCH_RESULTS = 20
RETRIES = 2
RETRY_STATUSES = frozenset({502, 503, 504})

# English variants are preferred when present; the plain field is the product's main language.
_SOURCE_FIELDS = {
    "product_name": ("product_name_en", "product_name"),
    "brands": ("brands",),
    "ingredients_text": ("ingredients_text_en", "ingredients_text"),
    "categories": ("categories",),
    "quantity": ("quantity",),
    "nutriscore_grade": ("nutriscore_grade",),
}
_REQUESTED_FIELDS = ",".join(
    ["code", *dict.fromkeys(name for names in _SOURCE_FIELDS.values() for name in names)]
)
_VALID_GRADES = frozenset("abcde")


class ExternalAPIError(Exception):
    """OpenFoodFacts could not be reached or sent back something unusable."""


class OpenFoodFactsClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        session: requests.Session | None = None,
        timeout: float = TIMEOUT_SECONDS,
        retry_delay: float = 1.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout
        self.retry_delay = retry_delay

    def get_product(self, barcode: str) -> dict[str, Any] | None:
        """Return the normalized product, or ``None`` if OpenFoodFacts doesn't know it."""
        data = self._get(
            f"/api/v2/product/{barcode}.json",
            params={"fields": _REQUESTED_FIELDS},
            allow_not_found=True,
        )
        if data is None or data.get("status") != 1 or not isinstance(data.get("product"), dict):
            return None
        return normalize_product(data.get("code") or barcode, data["product"])

    def search(self, name: str, limit: int = 5) -> list[dict[str, Any]]:
        limit = max(1, min(limit, MAX_SEARCH_RESULTS))
        data = self._get(
            "/cgi/search.pl",
            params={
                "search_terms": name,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": limit,
                "fields": _REQUESTED_FIELDS,
            },
        )
        products = data.get("products") if isinstance(data, dict) else None
        if not isinstance(products, list):
            raise ExternalAPIError("OpenFoodFacts search returned an unexpected response")
        return [
            normalize_product(raw["code"], raw)
            for raw in products
            if isinstance(raw, dict) and raw.get("code")
        ][:limit]

    def _get(self, path: str, params: dict[str, Any], allow_not_found: bool = False) -> Any:
        # The search endpoint is rate-limited and sometimes answers 503, so retry briefly.
        for attempt in range(1 + RETRIES):
            try:
                response = self.session.get(
                    f"{self.base_url}{path}",
                    params=params,
                    headers={"User-Agent": USER_AGENT},
                    timeout=self.timeout,
                )
            except requests.RequestException as error:
                raise ExternalAPIError(f"Could not reach OpenFoodFacts: {error}") from error
            if response.status_code not in RETRY_STATUSES or attempt == RETRIES:
                break
            time.sleep(self.retry_delay)

        if allow_not_found and response.status_code == 404:
            return None
        if not response.ok:
            raise ExternalAPIError(f"OpenFoodFacts responded with HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as error:
            raise ExternalAPIError("OpenFoodFacts returned invalid JSON") from error


def normalize_product(barcode: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw OpenFoodFacts product onto the inventory's ``product`` fields."""
    product = {}
    for field in PRODUCT_FIELDS:
        value = _first_text(raw, _SOURCE_FIELDS[field])
        if value:
            product[field] = value

    grade = product.get("nutriscore_grade", "").lower()
    product = {key: value for key, value in product.items() if key != "nutriscore_grade"}
    if grade in _VALID_GRADES:
        product["nutriscore_grade"] = grade

    product.setdefault("product_name", "Unnamed product")
    return {"barcode": str(barcode), "product": product}


def _first_text(raw: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""
