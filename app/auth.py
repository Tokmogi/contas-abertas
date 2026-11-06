from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .models import Convite, Organizacao, Usuario
from .utils import gerar_slug

bp = Blueprint("auth", __name__)


def _validar_pessoa(nome: str, email: str, senha: str) -> str | None:
    """Devolve a mensagem de erro, ou None se os dados da pessoa estiverem certos."""
    if not (nome and email and senha):
        return "Preencha todos os campos obrigatórios."
    if len(nome) > 120 or len(email) > 160 or "@" not in email:
        return "Confira seu nome e e-mail."
    if len(senha) < 8:
        return "A senha precisa ter pelo menos 8 caracteres."
    if Usuario.query.filter_by(email=email).first():
        return "Já existe uma conta com esse e-mail."
    return None


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        f = request.form
        nome_org = f.get("organizacao", "").strip()
        nome = f.get("nome", "").strip()
        email = f.get("email", "").strip().lower()
        senha = f.get("senha", "")

        if not nome_org:
            erro = "Preencha todos os campos obrigatórios."
        elif len(nome_org) > 120 or len(f.get("causa", "")) > 200 or len(f.get("cnpj", "")) > 18:
            erro = "Algum campo ficou comprido demais. Resuma e tente de novo."
        else:
            erro = _validar_pessoa(nome, email, senha)

        if erro:
            flash(erro, "erro")
            return render_template("auth/cadastro.html", form=f), 400

        slug_base = slug = gerar_slug(nome_org)
        n = 2
        while Organizacao.query.filter_by(slug=slug).first():
            slug = f"{slug_base}-{n}"
            n += 1

        org = Organizacao(
            nome=nome_org, slug=slug, cnpj=f.get("cnpj", "").strip(), causa=f.get("causa", "").strip()
        )
        usuario = Usuario(nome=nome, email=email, organizacao=org)
        usuario.definir_senha(senha)
        db.session.add_all([org, usuario])
        db.session.commit()

        login_user(usuario)
        flash("Organização cadastrada! Comece registrando as entradas e saídas.", "ok")
        return redirect(url_for("painel.inicio"))

    return render_template("auth/cadastro.html", form={})


@bp.route("/convite/<token>", methods=["GET", "POST"])
def convite(token: str):
    """Voluntário convidado cria a própria conta já dentro da organização."""
    conv = Convite.query.filter_by(token=token).first()
    if conv is None:
        abort(404)
    if not conv.valido:
        return render_template("auth/convite_invalido.html"), 410
    if current_user.is_authenticated:
        flash("Saia da sua conta atual para aceitar este convite.", "erro")
        return redirect(url_for("painel.inicio"))

    if request.method == "POST":
        f = request.form
        nome = f.get("nome", "").strip()
        email = f.get("email", "").strip().lower()
        senha = f.get("senha", "")
        erro = _validar_pessoa(nome, email, senha)
        if erro:
            flash(erro, "erro")
            return render_template("auth/convite.html", conv=conv, form=f), 400

        # Marca o convite como usado só se ninguém o usou antes (dois cliques ao mesmo tempo)
        marcados = Convite.query.filter_by(id=conv.id, usado_em=None).update(
            {"usado_em": datetime.now(timezone.utc)}
        )
        if not marcados:
            db.session.rollback()
            return render_template("auth/convite_invalido.html"), 410
        usuario = Usuario(nome=nome, email=email, organizacao_id=conv.organizacao_id)
        usuario.definir_senha(senha)
        db.session.add(usuario)
        db.session.commit()

        login_user(usuario)
        flash(f"Bem-vindo(a) à equipe de {conv.organizacao.nome}!", "ok")
        return redirect(url_for("painel.inicio"))

    return render_template("auth/convite.html", conv=conv, form={})


def _destino_seguro(destino: str | None) -> str:
    """Só aceita caminhos deste site (evita redirecionar para sites maliciosos)."""
    if (destino and destino.startswith("/") and not destino.startswith("//")
            and not any(ord(c) < 32 or c.isspace() or c == "\\" for c in destino)):
        partes = urlsplit(destino)
        if not partes.scheme and not partes.netloc:
            return destino
    return url_for("painel.inicio")


@bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    if current_user.is_authenticated:
        return redirect(url_for("painel.inicio"))
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.conferir_senha(request.form.get("senha", "")):
            login_user(usuario, remember=bool(request.form.get("lembrar")))
            return redirect(_destino_seguro(request.args.get("next")))
        flash("E-mail ou senha incorretos.", "erro")
    return render_template("auth/entrar.html", email=email)


@bp.route("/sair")
@login_required
def sair():
    logout_user()
    return redirect(url_for("publico.inicio"))
