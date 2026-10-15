"""Interactive menu, driven by scripted input against the Flask app."""

import pytest

from inventory_cli.menu import Menu
from tests.conftest import ALMOND_MILK


def run_menu(api, *answers):
    replies = iter(answers)
    output = []
    Menu(api, ask=lambda prompt: next(replies), say=output.append).run()
    return "\n".join(output)


def test_quit_immediately(api):
    assert "=== Inventory Admin ===" in run_menu(api, "q")


def test_invalid_option(api):
    assert "Not a valid option." in run_menu(api, "99", "q")


def test_list_with_and_without_search(api):
    out = run_menu(api, "1", "", "1", "nutella", "q")
    assert out.count("Nutella") == 2 and "Cheerios" in out


def test_view(api):
    assert "#4 Cheerios" in run_menu(api, "2", "4", "q")


def test_view_missing_shows_error_and_keeps_running(api):
    out = run_menu(api, "2", "999", "q")
    assert "Error: Item 999 not found" in out


def test_non_numeric_id(api):
    assert "Invalid input" in run_menu(api, "2", "abc", "q")


def test_add(api):
    # barcode, name, brand, size, categories, nutriscore, ingredients, price, stock
    out = run_menu(api, "3", "0028400090858", "Chips", "Lay's", "", "", "", "", "1.5", "10", "q")
    assert "Added item #6" in out
    assert api.get_item(6)["product"] == {"product_name": "Chips", "brands": "Lay's"}


def test_add_requires_name(api):
    out = run_menu(api, "3", "0028400090858", "", "", "", "", "", "", "q")
    assert "product name is required" in out
    assert len(api.list_items()) == 5


def test_update_changes_only_answered_fields(api):
    # id, six product prompts, price, stock
    out = run_menu(api, "4", "1", "", "Silk Inc", "", "", "", "", "", "3", "q")
    assert "Updated." in out
    item = api.get_item(1)
    assert item["stock"] == 3 and item["price"] == 4.49 and item["product"]["brands"] == "Silk Inc"


def test_update_with_new_price(api):
    run_menu(api, "4", "1", "", "", "", "", "", "", "5.25", "", "q")
    assert api.get_item(1)["price"] == 5.25


def test_update_with_no_changes(api):
    out = run_menu(api, "4", "1", "", "", "", "", "", "", "", "", "q")
    assert "Nothing changed." in out


@pytest.mark.parametrize("answer, remaining", [("y", 4), ("n", 5)])
def test_delete(api, answer, remaining):
    run_menu(api, "5", "2", answer, "q")
    assert len(api.list_items()) == remaining


def test_low_stock(api):
    out = run_menu(api, "8", "0", "q")
    assert "Original Potato Crisps" in out and "Nutella" not in out


def test_lookup_then_import(api):
    out = run_menu(api, "6", ALMOND_MILK["barcode"], "y", "3.49", "8", "q")
    assert "Organic Almond Milk" in out and "Imported as item #6" in out
    assert api.get_item(6)["stock"] == 8


def test_lookup_without_import(api):
    run_menu(api, "6", ALMOND_MILK["barcode"], "n", "q")
    assert len(api.list_items()) == 5


def test_lookup_unknown_barcode(api):
    assert "No OpenFoodFacts product" in run_menu(api, "6", "99999999", "q")


def test_search_then_import_selected_result(api):
    out = run_menu(api, "7", "almond", "1", "2.99", "5", "q")
    assert "1. Organic Almond Milk" in out and "Imported as item #6" in out


def test_search_skip_import(api):
    run_menu(api, "7", "almond", "", "q")
    assert len(api.list_items()) == 5


def test_search_invalid_choice(api):
    assert "Not a valid result number." in run_menu(api, "7", "almond", "9", "q")


def test_search_no_results(api):
    assert "No OpenFoodFacts products matched." in run_menu(api, "7", "zzz", "q")
