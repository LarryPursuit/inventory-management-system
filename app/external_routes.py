"""Routes backed by OpenFoodFacts: preview lookups and importing into inventory."""

from flask import Blueprint, current_app, jsonify, request

from app.openfoodfacts import MAX_SEARCH_RESULTS, ExternalAPIError, OpenFoodFactsClient
from app.routes import error_response, get_repository
from app.validation import is_valid_barcode, validate_import_request

external_bp = Blueprint("external", __name__, url_prefix="/api")


def get_food_client() -> OpenFoodFactsClient:
    return current_app.extensions["food_client"]


@external_bp.errorhandler(ExternalAPIError)
def handle_external_error(error: ExternalAPIError):
    current_app.logger.warning("OpenFoodFacts request failed: %s", error)
    return error_response("OpenFoodFacts is unavailable right now, try again later", 502)


@external_bp.get("/external/product/<barcode>")
def lookup_product(barcode: str):
    if not is_valid_barcode(barcode):
        return error_response("'barcode' must be a string of 8-14 digits", 400)
    product = get_food_client().get_product(barcode)
    if product is None:
        return error_response(f"No OpenFoodFacts product with barcode {barcode}", 404)
    return jsonify(product)


@external_bp.get("/external/search")
def search_products():
    name = request.args.get("name", "").strip()
    if not name:
        return error_response("'name' query parameter is required", 400)

    limit = request.args.get("limit", "5")
    if not limit.isdigit() or not 1 <= int(limit) <= MAX_SEARCH_RESULTS:
        return error_response(f"'limit' must be an integer from 1 to {MAX_SEARCH_RESULTS}", 400)
    return jsonify(get_food_client().search(name, int(limit)))


@external_bp.post("/inventory/import")
def import_product():
    data, errors = validate_import_request(request.get_json(silent=True))
    if errors:
        return error_response("; ".join(errors), 400)

    repo = get_repository()
    barcode = data["barcode"]
    if repo.find_by_barcode(barcode):
        return error_response(f"An item with barcode {barcode} already exists", 409)

    found = get_food_client().get_product(barcode)
    if found is None:
        return error_response(f"No OpenFoodFacts product with barcode {barcode}", 404)

    item = repo.create({**found, "price": data["price"], "stock": data["stock"]})
    return jsonify(item), 201
