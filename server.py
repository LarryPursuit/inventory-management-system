"""Start the inventory API: ``pipenv run python server.py``.

Uses port 5555 by default because macOS AirPlay Receiver often holds 5000.
"""

import os

from app import create_app

DEFAULT_PORT = 5555

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    app.run(host="127.0.0.1", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
