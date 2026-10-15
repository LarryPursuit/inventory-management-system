# Design — Inventory Management System

## 1. Problem

A small retail store needs an admin tool for its inventory. Employees must be
able to **add, view, edit, and delete** items, and look up real product details
(name, brand, ingredients, Nutri-Score) from the **OpenFoodFacts** database by
barcode or name so they don't have to type them in by hand.

Deliverables:

- A Flask REST API with full CRUD on an in-memory inventory.
- An OpenFoodFacts integration that can look products up and import them.
- A command-line interface that talks to the API over HTTP.
- A pytest suite covering every feature.

## 2. Data model

The "database" is a Python list held by `InventoryRepository`
([app/repository.py](../app/repository.py)) and seeded from
[app/data.py](../app/data.py). Every record has an `id`.

The `product` block uses OpenFoodFacts' own field names, so a product fetched
from the API can be stored without renaming anything. For reference, a real
OpenFoodFacts response looks like:

```json
{
  "code": "0025293600232",
  "status": 1,
  "status_verbose": "product found",
  "product": {
    "product_name": "Organic Soymilk",
    "brands": "Silk",
    "ingredients_text": "Organic Soymilk (Filtered Water, Organic Soybeans), ...",
    "categories": "Soy-based drinks",
    "quantity": "64 fl oz",
    "nutriscore_grade": "b"
  }
}
```

An inventory record keeps that `product` block and adds what the store tracks:

```json
{
  "id": 1,
  "barcode": "0025293600232",
  "product": {
    "product_name": "Organic Soymilk",
    "brands": "Silk",
    "ingredients_text": "...",
    "categories": "Soy-based drinks",
    "quantity": "64 fl oz",
    "nutriscore_grade": "b"
  },
  "price": 4.49,
  "stock": 24
}
```

| Field | Type | Rules |
|-------|------|-------|
| `id` | int | Assigned by the server; can't be set or changed by clients |
| `barcode` | string | 8–14 digits; unique across the inventory |
| `product.product_name` | string | Required on create; non-empty |
| `product.brands`, `ingredients_text`, `categories`, `quantity` | string | Optional |
| `product.nutriscore_grade` | string | Optional; one of `a`–`e` |
| `price` | number | ≥ 0 |
| `stock` | int | ≥ 0 |

## 3. Routes

All routes are under `/api`. Errors return `{"error": "<message>"}` with a
matching status code.

| Method & path | Input | Output | Changes to data | Triggered from the CLI by |
|---|---|---|---|---|
| `GET /api/health` | — | `200 {"status": "ok", "items": <count>}` | None | `health` |
| `GET /api/inventory` | Query: optional `q` (search name/brand/category), `low_stock` (int threshold) | `200 [item, ...]` | None | `list`, `list --search milk`, `list --low-stock 5` |
| `GET /api/inventory/<id>` | Path: `id` | `200 item` · `404` | None | `view <id>` |
| `POST /api/inventory` | JSON: `barcode`, `product` (with `product_name`), `price`, `stock` | `201 item` · `400` invalid · `409` barcode exists | Appends a new record with the next `id` | `add` |
| `PATCH /api/inventory/<id>` | Path: `id`; JSON: any subset of `barcode`, `price`, `stock`, `product.*` | `200 item` · `400` · `404` · `409` | Replaces the record with the merged version; `product` fields merge, others overwrite | `update <id> --stock 10 ...` |
| `DELETE /api/inventory/<id>` | Path: `id` | `200 {"message", "item"}` · `404` | Removes the record | `delete <id>` |
| `GET /api/external/product/<barcode>` | Path: `barcode` | `200 {"barcode", "product"}` · `404` not on OpenFoodFacts · `502` upstream failure | None (preview only) | `lookup <barcode>` |
| `GET /api/external/search` | Query: `name` (required), `limit` (1–20, default 5) | `200 [{"barcode", "product"}, ...]` · `400` · `502` | None (preview only) | `find "<name>"` |
| `POST /api/inventory/import` | JSON: `barcode` (required), `price`, `stock` (default 0) | `201 item` · `400` · `404` · `409` · `502` | Fetches the product from OpenFoodFacts and appends it as a new record | `import <barcode> --price 3.99 --stock 12` |

## 4. Architecture

```
cli.py  ──HTTP──▶  Flask app (app/routes.py, app/external_routes.py)
                     │  validates input (app/validation.py)
                     ├─▶ InventoryRepository (app/repository.py) ◀─ seed (app/data.py)
                     └─▶ OpenFoodFactsClient (app/openfoodfacts.py) ──HTTP──▶ world.openfoodfacts.org
                                                                              search.openfoodfacts.org
```

- `create_app()` builds a fresh app with its own repository and OpenFoodFacts
  client, so each test gets clean data and a fake client can be injected.
- The repository never mutates records in place; reads return copies and an
  update swaps in a new dict.
- The OpenFoodFacts client uses the v2 product endpoint for barcodes and
  Search-a-licious (`search.openfoodfacts.org/search`) for name search, falling
  back to the legacy `cgi/search.pl` endpoint if that fails. It requests only
  the fields we store, sends a descriptive `User-Agent` as the API asks, retries
  503s briefly (the service is rate-limited), and turns network and HTTP
  failures into a single `ExternalAPIError`, which the routes return as `502`.

## 5. Testing

Each feature has its own test module; OpenFoodFacts and HTTP calls are mocked so
the suite runs offline. See the README for commands.
