"""Seed data for the in-memory inventory "database".

Each record mirrors the shape of an OpenFoodFacts product response
(``GET /api/v2/product/<barcode>.json``): the ``product`` block uses the same
field names OpenFoodFacts returns. Store-specific fields (``id``, ``price``,
``stock``) sit alongside it at the top level.

Barcodes and product details were taken from real OpenFoodFacts entries.
"""

PRODUCT_FIELDS = (
    "product_name",
    "brands",
    "ingredients_text",
    "categories",
    "quantity",
    "nutriscore_grade",
)

SEED_INVENTORY = (
    {
        "id": 1,
        "barcode": "0025293600232",
        "product": {
            "product_name": "Organic Soymilk",
            "brands": "Silk",
            "ingredients_text": "Organic Soymilk (Filtered Water, Organic Soybeans), "
            "Vitamin and Mineral Blend, Sea Salt, Gellan Gum, Natural Flavor.",
            "categories": "Soy-based drinks",
            "quantity": "64 fl oz",
            "nutriscore_grade": "b",
        },
        "price": 4.49,
        "stock": 24,
    },
    {
        "id": 2,
        "barcode": "3017620422003",
        "product": {
            "product_name": "Nutella",
            "brands": "Ferrero",
            "ingredients_text": "Sugar, palm oil, hazelnuts 13%, fat-reduced cocoa 7.4%, "
            "skimmed milk powder 6.6%, whey powder, lecithins (soya), vanillin.",
            "categories": "Hazelnut spreads",
            "quantity": "400 g",
            "nutriscore_grade": "e",
        },
        "price": 5.99,
        "stock": 12,
    },
    {
        "id": 3,
        "barcode": "5449000000996",
        "product": {
            "product_name": "Coca-Cola Original",
            "brands": "Coca-Cola",
            "ingredients_text": "Carbonated water, sugar, colour (caramel E150d), "
            "acid (phosphoric acid), natural flavourings including caffeine.",
            "categories": "Colas",
            "quantity": "330 ml",
            "nutriscore_grade": "e",
        },
        "price": 1.25,
        "stock": 96,
    },
    {
        "id": 4,
        "barcode": "0016000275287",
        "product": {
            "product_name": "Cheerios",
            "brands": "General Mills",
            "ingredients_text": "Whole grain oats, corn starch, sugar, salt, "
            "tripotassium phosphate, vitamin E (mixed tocopherols).",
            "categories": "Breakfast cereals",
            "quantity": "8.9 oz",
            "nutriscore_grade": "a",
        },
        "price": 4.29,
        "stock": 30,
    },
    {
        "id": 5,
        "barcode": "0038000138416",
        "product": {
            "product_name": "Original Potato Crisps",
            "brands": "Pringles",
            "ingredients_text": "Dried potatoes, vegetable oil, degerminated yellow corn "
            "flour, cornstarch, rice flour, maltodextrin, salt, wheat starch.",
            "categories": "Potato crisps",
            "quantity": "5.2 oz",
            "nutriscore_grade": "e",
        },
        "price": 2.79,
        "stock": 0,
    },
)
