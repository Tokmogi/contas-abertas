"""Contas Abertas: transparência financeira para organizações sociais."""
import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.entrar"
login_manager.login_message = "Entre para acessar o painel."


def criar_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///" + os.path.join(app.instance_path, "contas.db")
        ),
        UPLOAD_FOLDER=os.environ.get(
            "UPLOAD_FOLDER", os.path.join(app.instance_path, "comprovantes")
        ),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # comprovantes de até 5 MB
    )
    if config:
        app.config.update(config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from . import auth, painel, publico

    app.register_blueprint(auth.bp)
    app.register_blueprint(painel.bp)
    app.register_blueprint(publico.bp)

    from .utils import moeda

    app.jinja_env.filters["moeda"] = moeda

    with app.app_context():
        db.create_all()

    return app
