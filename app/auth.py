from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from . import db
from .models import Organizacao, Usuario
from .utils import gerar_slug

bp = Blueprint("auth", __name__)


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        f = request.form
        nome_org = f.get("organizacao", "").strip()
        nome = f.get("nome", "").strip()
        email = f.get("email", "").strip().lower()
        senha = f.get("senha", "")

        erro = None
        if not (nome_org and nome and email and senha):
            erro = "Preencha todos os campos obrigatórios."
        elif len(senha) < 8:
            erro = "A senha precisa ter pelo menos 8 caracteres."
        elif Usuario.query.filter_by(email=email).first():
            erro = "Já existe uma conta com esse e-mail."

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


@bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.conferir_senha(request.form.get("senha", "")):
            login_user(usuario)
            return redirect(url_for("painel.inicio"))
        flash("E-mail ou senha incorretos.", "erro")
    return render_template("auth/entrar.html")


@bp.route("/sair")
@login_required
def sair():
    logout_user()
    return redirect(url_for("publico.inicio"))
