"""Flask application factory for the inventory admin API."""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from app.repository import InventoryRepository
from app.routes import inventory_bp


def create_app(repository: InventoryRepository | None = None) -> Flask:
    """Build an app with its own data store, so each test starts from clean seed data."""
    app = Flask(__name__)
    app.json.sort_keys = False
    app.extensions["inventory"] = repository or InventoryRepository()

    app.register_blueprint(inventory_bp)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        # Keep every error response JSON, including Flask's own 404/405s.
        return jsonify({"error": error.description}), error.code

    return app
