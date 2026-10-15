"""Request-body validation for inventory routes.

Each validator returns ``(clean_data, errors)``. ``errors`` is a list of
human-readable messages; an empty list means the payload is valid.
"""

import re
from typing import Any

from app.data import PRODUCT_FIELDS

BARCODE_PATTERN = re.compile(r"^\d{8,14}$")
NUTRISCORE_GRADES = frozenset("abcde")
TOP_LEVEL_FIELDS = frozenset({"barcode", "product", "price", "stock"})

Payload = dict[str, Any]
Result = tuple[Payload, list[str]]


def validate_new_item(payload: Any) -> Result:
    clean, errors = _validate(payload)
    if errors:
        return clean, errors
    missing = [field for field in ("barcode", "product", "price", "stock") if field not in clean]
    errors = [f"'{field}' is required" for field in missing]
    if "product" in clean and "product_name" not in clean["product"]:
        errors.append("'product.product_name' is required")
    return clean, errors


def validate_item_changes(payload: Any) -> Result:
    clean, errors = _validate(payload)
    if not errors and not clean:
        errors.append("Provide at least one field to update")
    return clean, errors


def validate_import_request(payload: Any) -> Result:
    if not isinstance(payload, dict):
        return {}, ["Request body must be a JSON object"]
    if "barcode" not in payload:
        return {}, ["'barcode' is required"]
    extra = set(payload) - {"barcode", "price", "stock"}
    if extra:
        return {}, [f"Unknown field(s): {', '.join(sorted(extra))}"]
    clean, errors = _validate({"price": 0, "stock": 0, **payload})
    return clean, errors


def is_valid_barcode(value: Any) -> bool:
    return isinstance(value, str) and bool(BARCODE_PATTERN.match(value))


def _validate(payload: Any) -> Result:
    if not isinstance(payload, dict):
        return {}, ["Request body must be a JSON object"]

    unknown = set(payload) - TOP_LEVEL_FIELDS
    if unknown:
        return {}, [f"Unknown field(s): {', '.join(sorted(unknown))}"]

    checks = {
        "barcode": _check_barcode,
        "price": _check_price,
        "stock": _check_stock,
        "product": _check_product,
    }
    clean: Payload = {}
    errors: list[str] = []
    for field, check in checks.items():
        if field not in payload:
            continue
        value, field_errors = check(payload[field])
        errors.extend(field_errors)
        if not field_errors:
            clean[field] = value
    return clean, errors


def _check_barcode(value: Any) -> tuple[Any, list[str]]:
    if is_valid_barcode(value):
        return value, []
    return None, ["'barcode' must be a string of 8-14 digits"]


def _check_price(value: Any) -> tuple[Any, list[str]]:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return None, ["'price' must be a number >= 0"]
    return round(float(value), 2), []


def _check_stock(value: Any) -> tuple[Any, list[str]]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None, ["'stock' must be an integer >= 0"]
    return value, []


def _check_product(value: Any) -> tuple[Any, list[str]]:
    if not isinstance(value, dict):
        return None, ["'product' must be an object"]
    unknown = set(value) - set(PRODUCT_FIELDS)
    if unknown:
        return None, [f"Unknown product field(s): {', '.join(sorted(unknown))}"]

    errors = [
        f"'product.{key}' must be a string"
        for key, field_value in value.items()
        if not isinstance(field_value, str)
    ]
    if errors:
        return None, errors

    clean = {key: field_value.strip() for key, field_value in value.items()}
    if "product_name" in clean and not clean["product_name"]:
        errors.append("'product.product_name' cannot be empty")
    grade = clean.get("nutriscore_grade")
    if grade:
        clean = {**clean, "nutriscore_grade": grade.lower()}
        if clean["nutriscore_grade"] not in NUTRISCORE_GRADES:
            errors.append("'product.nutriscore_grade' must be one of a-e")
    return (None, errors) if errors else (clean, [])
