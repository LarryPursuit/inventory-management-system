"""Inventory CRUD routes plus helper routes (health, search, low-stock filter)."""

from flask import Blueprint, abort, current_app, jsonify, request

from app.repository import InventoryRepository
from app.validation import validate_item_changes, validate_new_item

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api")


def get_repository() -> InventoryRepository:
    return current_app.extensions["inventory"]


def error_response(message: str, status: int):
    return jsonify({"error": message}), status


@inventory_bp.get("/health")
def health():
    return jsonify({"status": "ok", "items": len(get_repository().find_all())})


@inventory_bp.get("/inventory")
def list_items():
    repo = get_repository()
    term = request.args.get("q", "").strip()
    items = repo.search(term) if term else repo.find_all()

    threshold = request.args.get("low_stock")
    if threshold is not None:
        if not threshold.isdigit():
            return error_response("'low_stock' must be a non-negative integer", 400)
        low_ids = {item["id"] for item in repo.low_stock(int(threshold))}
        items = [item for item in items if item["id"] in low_ids]
    return jsonify(items)


@inventory_bp.get("/inventory/<int:item_id>")
def get_item(item_id: int):
    item = get_repository().find_by_id(item_id)
    if item is None:
        abort(404, description=f"Item {item_id} not found")
    return jsonify(item)


@inventory_bp.post("/inventory")
def create_item():
    data, errors = validate_new_item(request.get_json(silent=True))
    if errors:
        return error_response("; ".join(errors), 400)

    repo = get_repository()
    if repo.find_by_barcode(data["barcode"]):
        return error_response(f"An item with barcode {data['barcode']} already exists", 409)
    return jsonify(repo.create(data)), 201


@inventory_bp.patch("/inventory/<int:item_id>")
def update_item(item_id: int):
    repo = get_repository()
    if repo.find_by_id(item_id) is None:
        abort(404, description=f"Item {item_id} not found")

    changes, errors = validate_item_changes(request.get_json(silent=True))
    if errors:
        return error_response("; ".join(errors), 400)

    existing = repo.find_by_barcode(changes["barcode"]) if "barcode" in changes else None
    if existing and existing["id"] != item_id:
        return error_response(f"An item with barcode {changes['barcode']} already exists", 409)
    return jsonify(repo.update(item_id, changes))


@inventory_bp.delete("/inventory/<int:item_id>")
def delete_item(item_id: int):
    removed = get_repository().delete(item_id)
    if removed is None:
        abort(404, description=f"Item {item_id} not found")
    return jsonify({"message": f"Item {item_id} deleted", "item": removed})
