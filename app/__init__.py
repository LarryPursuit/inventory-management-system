"""Flask application factory for the inventory admin API."""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from app.external_routes import external_bp
from app.openfoodfacts import OpenFoodFactsClient
from app.repository import InventoryRepository
from app.routes import inventory_bp


def create_app(
    repository: InventoryRepository | None = None,
    food_client: OpenFoodFactsClient | None = None,
) -> Flask:
    """Build an app with its own data store and OpenFoodFacts client.

    Tests pass a fresh repository and a fake client so they start from clean
    seed data and never hit the network.
    """
    app = Flask(__name__)
    app.json.sort_keys = False
    app.extensions["inventory"] = repository or InventoryRepository()
    app.extensions["food_client"] = food_client or OpenFoodFactsClient()

    app.register_blueprint(inventory_bp)
    app.register_blueprint(external_bp)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        # Keep every error response JSON, including Flask's own 404/405s.
        return jsonify({"error": error.description}), error.code

    return app
