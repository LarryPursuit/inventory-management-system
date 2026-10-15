"""CLI subcommands, run end-to-end through main() against the Flask app."""

import pytest

from inventory_cli.main import build_parser, build_product_changes, main
from tests.conftest import ALMOND_MILK


@pytest.fixture
def run(api, capsys):
    def _run(*argv):
        code = main(list(argv), api=api)
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return _run


def test_health(run):
    assert run("health") == (0, "API is ok — 5 item(s) in inventory.\n", "")


def test_list_and_filters(run):
    code, out, _ = run("list")
    assert code == 0 and "Nutella" in out and "Cheerios" in out
    _, out, _ = run("list", "--search", "silk")
    assert "Organic Soymilk" in out and "Nutella" not in out
    _, out, _ = run("list", "--low-stock", "0")
    assert "Original Potato Crisps" in out and "Nutella" not in out
    _, out, _ = run("list", "--search", "zzz")
    assert "No items found." in out


def test_view(run):
    code, out, _ = run("view", "2")
    assert code == 0
    assert "#2 Nutella" in out and "$5.99" in out


def test_view_missing_prints_error_and_exits_1(run):
    code, out, err = run("view", "999")
    assert code == 1
    assert out == ""
    assert err == "Error: Item 999 not found\n"


def test_add(run, api):
    code, out, _ = run(
        "add", "--barcode", "0028400090858", "--name", "Classic Potato Chips",
        "--brand", "Lay's", "--price", "1.5", "--stock", "40", "--nutriscore", "d",
    )
    assert code == 0
    assert "Added item #6" in out
    assert api.get_item(6)["product"] == {
        "product_name": "Classic Potato Chips", "brands": "Lay's", "nutriscore_grade": "d",
    }


def test_add_validation_error_from_api(run):
    code, _, err = run("add", "--barcode", "12", "--name", "X", "--price", "1", "--stock", "1")
    assert code == 1
    assert "8-14 digits" in err


def test_update(run, api):
    code, out, _ = run("update", "1", "--stock", "7", "--brand", "Silk Inc")
    assert code == 0 and "Updated item #1" in out
    item = api.get_item(1)
    assert item["stock"] == 7 and item["product"]["brands"] == "Silk Inc"


def test_update_with_no_options(run):
    code, _, err = run("update", "1")
    assert code == 1 and "Nothing to update" in err


def test_delete_with_yes_flag(run, api):
    code, out, _ = run("delete", "3", "--yes")
    assert code == 0 and "Item 3 deleted" in out
    assert len(api.list_items()) == 4


@pytest.mark.parametrize("answer, deleted", [("y", True), ("", False), ("no", False)])
def test_delete_confirmation_prompt(run, api, monkeypatch, answer, deleted):
    monkeypatch.setattr("builtins.input", lambda prompt: answer)
    _, out, _ = run("delete", "3")
    assert ("Item 3 deleted" in out) is deleted
    assert len(api.list_items()) == (4 if deleted else 5)


def test_lookup(run):
    code, out, _ = run("lookup", ALMOND_MILK["barcode"])
    assert code == 0
    assert "Organic Almond Milk" in out and "Nutri-Score: C" in out


def test_find(run):
    _, out, _ = run("find", "almond", "--limit", "3")
    assert f"1. Organic Almond Milk — Silk [{ALMOND_MILK['barcode']}]" in out
    _, out, _ = run("find", "nothing-matches")
    assert "No OpenFoodFacts products matched." in out


def test_import(run, api):
    code, out, _ = run("import", ALMOND_MILK["barcode"], "--price", "3.99", "--stock", "12")
    assert code == 0 and "Imported from OpenFoodFacts as item #6" in out
    assert api.get_item(6)["stock"] == 12


def test_import_duplicate(run):
    code, _, err = run("import", "3017620422003")
    assert code == 1 and "already exists" in err


def test_no_command_opens_menu(run, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "q")
    code, out, _ = run()
    assert code == 0
    assert "Inventory Admin" in out and "Goodbye!" in out


def test_ctrl_c_exits_cleanly(run, monkeypatch):
    def interrupt(prompt):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", interrupt)
    code, _, err = run("delete", "1")
    assert code == 130 and "Cancelled" in err


def test_build_product_changes_only_includes_given_options():
    args = build_parser().parse_args(["update", "1", "--price", "2", "--name", "New"])
    assert build_product_changes(args) == {"price": 2.0, "product": {"product_name": "New"}}
    args = build_parser().parse_args(["update", "1"])
    assert build_product_changes(args) == {}


def test_add_requires_name():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["add", "--barcode", "12345678", "--price", "1", "--stock", "1"])
