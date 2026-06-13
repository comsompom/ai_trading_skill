from __future__ import annotations

import os

from flask import Flask

from app.env import load_env_file
from app.routes import api


def create_app() -> Flask:
    load_env_file()
    app = Flask(__name__)
    app.register_blueprint(api)
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
