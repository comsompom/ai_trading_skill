from __future__ import annotations

from flask import Flask

from app.routes import api


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(api)
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)

