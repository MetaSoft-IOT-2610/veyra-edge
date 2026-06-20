"""Flask application entry point for the Veyra Edge Service.

This module wires together the Flask application, registers the IAM and
Monitoring bounded-context Blueprints, and ensures the SQLite database is
initialized (tables created) exactly once before the first HTTP request is
handled.

Environment variables are loaded from a ``.env`` file (when present) before any
configuration module is imported, so a single codebase runs unchanged across
local development and on-premise edge deployments.

Typical usage::

    flask --app app run
    # or
    python app.py
"""
from dotenv import load_dotenv

# Load .env before importing modules that read configuration at import time.
load_dotenv(override=True)

import logging  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from flask import Flask  # noqa: E402 (import after dotenv on purpose)

from iam.interfaces.services import iam_api  # noqa: E402
from monitoring.interfaces.services import monitoring_api  # noqa: E402
from shared.infrastructure.database import init_db  # noqa: E402
from shared.infrastructure.node_seed import seed_registered_nodes  # noqa: E402

app = Flask(__name__)
app.register_blueprint(iam_api)
app.register_blueprint(monitoring_api)

first_request = True


def bootstrap() -> None:
    """Create tables and seed test nodes (idempotent)."""
    init_db()
    seed_registered_nodes()


@app.before_request
def setup():
    """Initialize the database on the very first request.

    Uses a module-level flag (``first_request``) to ensure this one-time setup
    runs only once for the lifetime of the process.  Subsequent requests bypass
    this function entirely.

    Side effects:
        - Creates the configured SQLite database file if absent.
        - Creates the ``devices`` and ``measurements`` tables if they do not
          exist yet (``safe=True``).
        - Registers nodes from the optional seed file (``nodes.seed.json``).
    """
    global first_request
    if first_request:
        first_request = False
        bootstrap()


if __name__ == "__main__":
    bootstrap()
    app.run(host="0.0.0.0", port=5000, debug=True)
