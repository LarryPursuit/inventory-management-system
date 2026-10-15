import pytest

from app.validation import (
    is_valid_barcode,
    validate_import_request,
    validate_item_changes,
    validate_new_item,
)

VALID = {
    "barcode": "12345678",
    "product": {"product_name": "  Oat Milk  "},
    "price": 3,
    "stock": 2,
}


def test_valid_new_item_is_cleaned():
    clean, errors = validate_new_item(VALID)
    assert errors == []
    assert clean["product"]["product_name"] == "Oat Milk"
    assert clean["price"] == 3.0


@pytest.mark.parametrize("payload", [None, [], "text", 5])
def test_body_must_be_object(payload):
    assert validate_new_item(payload)[1] == ["Request body must be a JSON object"]


@pytest.mark.parametrize("barcode", ["1234567", "123456789012345", "abcdefgh", 12345678, ""])
def test_invalid_barcodes(barcode):
    assert not is_valid_barcode(barcode)
    assert validate_new_item({**VALID, "barcode": barcode})[1]


@pytest.mark.parametrize("price", [-1, "3.00", True, None])
def test_invalid_price(price):
    assert validate_new_item({**VALID, "price": price})[1] == ["'price' must be a number >= 0"]


@pytest.mark.parametrize("stock", [-1, 1.5, "2", False])
def test_invalid_stock(stock):
    assert validate_new_item({**VALID, "stock": stock})[1] == ["'stock' must be an integer >= 0"]


def test_price_is_rounded_to_cents():
    assert validate_new_item({**VALID, "price": 1.239})[0]["price"] == 1.24


def test_product_must_be_object():
    assert validate_new_item({**VALID, "product": "Oat Milk"})[1] == ["'product' must be an object"]


def test_unknown_product_field():
    errors = validate_new_item({**VALID, "product": {"product_name": "x", "color": "red"}})[1]
    assert errors == ["Unknown product field(s): color"]


def test_product_values_must_be_strings():
    errors = validate_new_item({**VALID, "product": {"product_name": 7}})[1]
    assert errors == ["'product.product_name' must be a string"]


def test_product_name_cannot_be_blank():
    errors = validate_new_item({**VALID, "product": {"product_name": "  "}})[1]
    assert errors == ["'product.product_name' cannot be empty"]


def test_nutriscore_grade_is_lowercased_and_checked():
    ok = validate_new_item({**VALID, "product": {"product_name": "x", "nutriscore_grade": "A"}})
    assert ok[0]["product"]["nutriscore_grade"] == "a"
    bad = validate_new_item({**VALID, "product": {"product_name": "x", "nutriscore_grade": "z"}})
    assert bad[1] == ["'product.nutriscore_grade' must be one of a-e"]


def test_multiple_errors_are_reported_together():
    errors = validate_new_item({**VALID, "price": -1, "stock": -1})[1]
    assert len(errors) == 2


def test_changes_allow_partial_payload():
    clean, errors = validate_item_changes({"stock": 9})
    assert (clean, errors) == ({"stock": 9}, [])


def test_changes_do_not_require_product_name():
    clean, errors = validate_item_changes({"product": {"brands": "Oatly"}})
    assert errors == []


def test_changes_reject_empty_and_unknown():
    assert validate_item_changes({})[1] == ["Provide at least one field to update"]
    assert validate_item_changes({"id": 3})[1] == ["Unknown field(s): id"]


def test_import_request_defaults_price_and_stock():
    clean, errors = validate_import_request({"barcode": "3017620422003"})
    assert errors == []
    assert clean == {"barcode": "3017620422003", "price": 0.0, "stock": 0}


def test_import_request_errors():
    assert validate_import_request(None)[1] == ["Request body must be a JSON object"]
    assert validate_import_request({})[1] == ["'barcode' is required"]
    assert validate_import_request({"barcode": "12345678", "product": {}})[1] == [
        "Unknown field(s): product"
    ]
    assert validate_import_request({"barcode": "12", "stock": 1})[1]
