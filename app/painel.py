"""Área restrita: a organização registra entradas, saídas e comprovantes."""
import csv
import io
import os
import uuid
from datetime import date

from flask import (
    Blueprint, Response, abort, current_app, flash, redirect, render_template,
    request, send_from_directory, url_for,
)
from flask_login import current_user, login_required

from . import db
from .models import CATEGORIAS_DESPESA, CATEGORIAS_RECEITA, Lancamento
from .utils import ler_valor, resumo

bp = Blueprint("painel", __name__, url_prefix="/painel")

EXTENSOES = {"pdf", "png", "jpg", "jpeg", "webp"}


def _lancamentos_da_org():
    return Lancamento.query.filter_by(organizacao_id=current_user.organizacao_id)


def _lancamento_ou_404(lanc_id: int) -> Lancamento:
    lanc = _lancamentos_da_org().filter_by(id=lanc_id).first()
    if lanc is None:
        abort(404)
    return lanc


def _salvar_comprovante(arquivo) -> str | None:
    if not arquivo or not arquivo.filename:
        return None
    ext = arquivo.filename.rsplit(".", 1)[-1].lower() if "." in arquivo.filename else ""
    if ext not in EXTENSOES:
        raise ValueError("Comprovante deve ser PDF ou imagem (PNG, JPG, WEBP).")
    nome = f"{uuid.uuid4().hex}.{ext}"
    arquivo.save(os.path.join(current_app.config["UPLOAD_FOLDER"], nome))
    return nome


@bp.route("/")
@login_required
def inicio():
    lancamentos = _lancamentos_da_org().order_by(Lancamento.data.desc(), Lancamento.id.desc()).all()
    return render_template(
        "painel/inicio.html", lancamentos=lancamentos, resumo=resumo(lancamentos)
    )


@bp.route("/lancamentos/novo", methods=["GET", "POST"])
@bp.route("/lancamentos/<int:lanc_id>/editar", methods=["GET", "POST"])
@login_required
def formulario(lanc_id: int | None = None):
    lanc = _lancamento_ou_404(lanc_id) if lanc_id else None

    if request.method == "POST":
        f = request.form
        try:
            tipo = f.get("tipo")
            if tipo not in ("receita", "despesa"):
                raise ValueError("Escolha se é entrada ou saída.")
            categorias = CATEGORIAS_RECEITA if tipo == "receita" else CATEGORIAS_DESPESA
            if f.get("categoria") not in categorias:
                raise ValueError("Escolha uma categoria válida.")
            descricao = f.get("descricao", "").strip()
            if not descricao:
                raise ValueError("Informe uma descrição.")
            valor = ler_valor(f.get("valor"))
            data_lanc = date.fromisoformat(f.get("data") or date.today().isoformat())
            comprovante = _salvar_comprovante(request.files.get("comprovante"))
        except ValueError as e:
            flash(str(e), "erro")
            return render_template(
                "painel/formulario.html", lanc=lanc, form=f,
                receitas=CATEGORIAS_RECEITA, despesas=CATEGORIAS_DESPESA,
            ), 400

        if lanc is None:
            lanc = Lancamento(organizacao_id=current_user.organizacao_id)
            db.session.add(lanc)
        lanc.tipo, lanc.categoria, lanc.descricao = tipo, f["categoria"], descricao
        lanc.valor, lanc.data = valor, data_lanc
        if comprovante:
            lanc.comprovante = comprovante
        db.session.commit()
        flash("Lançamento salvo.", "ok")
        return redirect(url_for("painel.inicio"))

    return render_template(
        "painel/formulario.html", lanc=lanc, form={},
        receitas=CATEGORIAS_RECEITA, despesas=CATEGORIAS_DESPESA,
    )


@bp.route("/lancamentos/<int:lanc_id>/excluir", methods=["POST"])
@login_required
def excluir(lanc_id: int):
    db.session.delete(_lancamento_ou_404(lanc_id))
    db.session.commit()
    flash("Lançamento excluído.", "ok")
    return redirect(url_for("painel.inicio"))


@bp.route("/comprovantes/<int:lanc_id>")
@login_required
def comprovante(lanc_id: int):
    lanc = _lancamento_ou_404(lanc_id)
    if not lanc.comprovante:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], lanc.comprovante)


@bp.route("/exportar.csv")
@login_required
def exportar_csv():
    """Planilha para prestação de contas em editais (abre direto no Excel)."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(["Data", "Tipo", "Categoria", "Descrição", "Valor", "Tem comprovante"])
    for l in _lancamentos_da_org().order_by(Lancamento.data).all():
        escritor.writerow([
            l.data.strftime("%d/%m/%Y"), l.tipo, l.categoria, l.descricao,
            f"{l.valor:.2f}".replace(".", ","), "sim" if l.comprovante else "não",
        ])
    return Response(
        "﻿" + saida.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=prestacao-de-contas.csv"},
    )


@bp.route("/configuracoes", methods=["GET", "POST"])
@login_required
def configuracoes():
    org = current_user.organizacao
    if request.method == "POST":
        org.nome = request.form.get("nome", org.nome).strip() or org.nome
        org.causa = request.form.get("causa", "").strip()
        org.cnpj = request.form.get("cnpj", "").strip()
        org.publico = request.form.get("publico") == "on"
        db.session.commit()
        flash("Configurações salvas.", "ok")
        return redirect(url_for("painel.configuracoes"))
    return render_template("painel/configuracoes.html", org=org)
