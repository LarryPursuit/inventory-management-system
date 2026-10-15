from inventory_cli.display import format_item, format_product, format_search_results, format_table

ITEM = {
    "id": 9,
    "barcode": "12345678",
    "product": {"product_name": "A" * 40, "brands": "Brand", "nutriscore_grade": "b"},
    "price": 2,
    "stock": 0,
}


def test_table_truncates_long_names_and_formats_price():
    table = format_table([ITEM])
    assert "A" * 27 + "…" in table
    assert "$2.00" in table


def test_empty_table():
    assert format_table([]) == "No items found."


def test_item_flags_out_of_stock_and_uppercases_grade():
    text = format_item(ITEM)
    assert "out of stock" in text and "Nutri-Score: B" in text


def test_product_skips_missing_fields():
    text = format_product({"barcode": "1", "product": {"product_name": "Water"}})
    assert text == "Water\n  Barcode:     1"


def test_search_results_without_brand():
    assert format_search_results([{"barcode": "1", "product": {"product_name": "Water"}}]) == " 1. Water [1]"
