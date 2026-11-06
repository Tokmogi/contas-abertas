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
        # comprovantes de até 5 MB (+ folga para os outros campos do formulário)
        MAX_CONTENT_LENGTH=5 * 1024 * 1024 + 256 * 1024,
    )
    if config:
        app.config.update(config)
    if app.config["SECRET_KEY"] == "troque-esta-chave-em-producao" and not (app.debug or app.testing):
        app.logger.warning(
            "SECRET_KEY padrão em uso: defina a variável de ambiente SECRET_KEY antes de publicar o site."
        )
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .seguranca import conferir_csrf

    conferir_csrf(app)

    from . import auth, painel, publico

    app.register_blueprint(auth.bp)
    app.register_blueprint(painel.bp)
    app.register_blueprint(publico.bp)

    from .utils import mes_por_extenso, moeda

    app.jinja_env.filters["moeda"] = moeda
    app.jinja_env.filters["mes"] = mes_por_extenso
    _registrar_paginas_de_erro(app)

    with app.app_context():
        db.create_all()

    return app


ERROS = {
    400: ("Algo deu errado no envio", "Volte, recarregue a página e tente de novo."),
    404: ("Página não encontrada", "O endereço pode estar errado ou a página foi removida."),
    413: ("Arquivo muito grande", "O comprovante pode ter no máximo 5 MB. Tente uma foto menor ou um PDF."),
    500: ("Erro no sistema", "Não foi culpa sua. Tente de novo daqui a pouco."),
}


def _registrar_paginas_de_erro(app: Flask) -> None:
    from flask import render_template
    from werkzeug.exceptions import HTTPException

    def tratar(erro: HTTPException):
        titulo, mensagem = ERROS.get(erro.code, ERROS[500])
        if erro.code == 400 and erro.description and not erro.description.startswith("The browser"):
            mensagem = erro.description  # mensagem própria, ex.: formulário expirado
        return render_template("erro.html", titulo=titulo, mensagem=mensagem), erro.code

    for codigo in ERROS:
        app.register_error_handler(codigo, tratar)
