# Inventory Management System

An admin portal backend for a small retail store. Employees can add, view,
edit, and delete inventory items through a **Flask REST API**, pull real product
details from **[OpenFoodFacts](https://openfoodfacts.github.io/openfoodfacts-server/api/)**
by barcode or name, and do all of it from a **command-line interface**.

- Full CRUD on an in-memory inventory (`GET`, `POST`, `PATCH`, `DELETE`)
- Helper routes: health check, search, low-stock filter
- OpenFoodFacts lookup, name search, and one-step import into the inventory
- CLI with subcommands and an interactive menu
- 160 pytest tests, 100% line coverage, no network needed

The route design (inputs, outputs, data changes, and which CLI command calls
each route) is in **[docs/DESIGN.md](docs/DESIGN.md)**.

## Requirements

- Python 3.11+ (developed on 3.14)
- [pipenv](https://pipenv.pypa.io/)

## Setup

```bash
git clone <this repo>
cd inventory-management-system
pipenv install --dev
```

## Running

Start the API in one terminal:

```bash
pipenv run python server.py
```

It listens on `http://127.0.0.1:5555`. (Port 5000 is avoided because macOS
AirPlay Receiver often holds it.) Set `PORT` to change it, or `FLASK_DEBUG=1`
for auto-reload.

Use the CLI from a second terminal:

```bash
pipenv run python cli.py            # interactive menu
pipenv run python cli.py --help     # list every command
```

If the API runs somewhere else, pass `--api-url` or set `INVENTORY_API_URL`.

### CLI commands

| Command | What it does | API route |
|---|---|---|
| `health` | Check the API is up | `GET /api/health` |
| `list [--search TEXT] [--low-stock N]` | Show inventory as a table | `GET /api/inventory` |
| `view ID` | Show one item in detail | `GET /api/inventory/<id>` |
| `add --barcode B --name N --price P --stock S [--brand ...]` | Add an item by hand | `POST /api/inventory` |
| `update ID [--stock S] [--price P] [--name N] ...` | Change only the fields given | `PATCH /api/inventory/<id>` |
| `delete ID [-y]` | Remove an item (asks to confirm unless `-y`) | `DELETE /api/inventory/<id>` |
| `lookup BARCODE` | Preview a product from OpenFoodFacts | `GET /api/external/product/<barcode>` |
| `find NAME [--limit N]` | Search OpenFoodFacts by name | `GET /api/external/search` |
| `import BARCODE [--price P] [--stock S]` | Fetch from OpenFoodFacts and add to inventory | `POST /api/inventory/import` |
| `menu` | Interactive menu (the default) | all of the above |

Product options for `add`/`update`: `--name`, `--brand`, `--ingredients`,
`--categories`, `--size`, `--nutriscore`.

In the interactive menu, **Search OpenFoodFacts by name** shows numbered
results and lets you pick one to import with a price and stock count.

### Example session

```text
$ pipenv run python cli.py find "almond milk" --limit 3
 1. Almond Milk — Milbona [20050894]
 2. Almond milk chocolate — Blue Diamond Growers [4157006837]
 3. Almond milk chocolate — Blue Diamond Growers [0004157006837]

$ pipenv run python cli.py import 20050894 --price 3.49 --stock 10
Imported from OpenFoodFacts as item #6.
#6 Almond Milk
  Barcode:     20050894
  Brand:       Milbona
  Size:        1 l
  Categories:  Almond-based drinks
  Nutri-Score: C
  Ingredients: water, 6% cane sugar, 2% almonds, stabilizer: gellan gum; natural aroma.
  Price:       $3.49
  Stock:       10

$ pipenv run python cli.py update 6 --stock 4
$ pipenv run python cli.py list --low-stock 5
  ID  Barcode         Name                          Brand                Price  Stock
-------------------------------------------------------------------------------------
   5  0038000138416   Original Potato Crisps        Pringles             $2.79      0
   6  20050894        Almond Milk                   Milbona              $3.49      4
```

## API reference

All routes are under `/api` and return JSON. Errors look like
`{"error": "Item 99 not found"}`.

```bash
# list / search / filter
curl http://127.0.0.1:5555/api/inventory
curl "http://127.0.0.1:5555/api/inventory?q=nutella"
curl "http://127.0.0.1:5555/api/inventory?low_stock=10"

# create
curl -X POST http://127.0.0.1:5555/api/inventory \
  -H "Content-Type: application/json" \
  -d '{"barcode": "0028400090858", "product": {"product_name": "Classic Potato Chips", "brands": "Lay'"'"'s"}, "price": 1.5, "stock": 40}'

# partial update
curl -X PATCH http://127.0.0.1:5555/api/inventory/1 \
  -H "Content-Type: application/json" -d '{"stock": 10}'

# delete
curl -X DELETE http://127.0.0.1:5555/api/inventory/1

# OpenFoodFacts
curl http://127.0.0.1:5555/api/external/product/3017620422003
curl "http://127.0.0.1:5555/api/external/search?name=almond%20milk&limit=3"
curl -X POST http://127.0.0.1:5555/api/inventory/import \
  -H "Content-Type: application/json" -d '{"barcode": "0028400090858", "price": 1.49, "stock": 30}'
```

| Status | Meaning |
|---|---|
| `200` / `201` | Success / created |
| `400` | Invalid input (bad barcode, negative stock, unknown field, ...) |
| `404` | Item or OpenFoodFacts product not found |
| `409` | Barcode already in the inventory |
| `502` | OpenFoodFacts is unreachable or returned an error |

### Data shape

Records keep OpenFoodFacts' field names in a `product` block, so imported
products drop straight in. Store-only fields sit beside it:

```json
{
  "id": 1,
  "barcode": "0025293600232",
  "product": {
    "product_name": "Organic Soymilk",
    "brands": "Silk",
    "ingredients_text": "Organic Soymilk (Filtered Water, Organic Soybeans), ...",
    "categories": "Soy-based drinks",
    "quantity": "64 fl oz",
    "nutriscore_grade": "b"
  },
  "price": 4.49,
  "stock": 24
}
```

The inventory is seeded with five real OpenFoodFacts products
([app/data.py](app/data.py)) and lives in memory, so it resets when the server
restarts.

## Project structure

```
app/
  __init__.py          create_app() factory, JSON error handler
  data.py              seed inventory (OpenFoodFacts-shaped)
  repository.py        InventoryRepository: in-memory store, no in-place mutation
  validation.py        request-body validation
  routes.py            CRUD + helper routes
  external_routes.py   OpenFoodFacts lookup, search, import routes
  openfoodfacts.py     OpenFoodFacts HTTP client + response normalization
inventory_cli/
  api_client.py        HTTP client for the inventory API
  main.py              argparse subcommands
  menu.py              interactive menu
  display.py           table/detail formatting
server.py              runs the API
cli.py                 runs the CLI
docs/DESIGN.md         problem, data model, route design, architecture
tests/                 one test module per feature
```

## Testing

```bash
pipenv run pytest
pipenv run pytest --cov=app --cov=inventory_cli --cov-report=term-missing
```

The suite never touches the network: route tests inject a fake OpenFoodFacts
client, client tests mock `requests`, and CLI tests send their HTTP calls
straight into the Flask test client.

| Feature | Test module |
|---|---|
| Mock database / repository | `tests/test_repository.py` |
| Input validation | `tests/test_validation.py` |
| CRUD routes | `tests/test_crud_routes.py` |
| Helper routes (health, search, low stock, JSON errors) | `tests/test_helper_routes.py` |
| OpenFoodFacts client | `tests/test_openfoodfacts_client.py` |
| External API routes + import | `tests/test_external_routes.py` |
| CLI API client | `tests/test_cli_api_client.py` |
| CLI commands | `tests/test_cli_commands.py` |
| Interactive menu | `tests/test_cli_menu.py` |
| Output formatting | `tests/test_display.py` |

## Notes and limitations

- Data is in memory only; restarting the server restores the seed data.
- OpenFoodFacts name search uses Search-a-licious and falls back to the legacy
  `cgi/search.pl` endpoint, which is rate-limited and often returns 503. If
  both are down, the API returns `502` and the CLI says so.
- OpenFoodFacts data is crowd-sourced, so names, categories, and Nutri-Scores
  may be missing or in another language. English fields are used when present.
- There is no authentication; this is meant to run locally for store staff.

## Git workflow

Each feature was built on its own branch and merged into `main`:
`feature/mock-data` → `feature/crud-routes` → `feature/external-api` →
`feature/cli` → `docs/readme`.
