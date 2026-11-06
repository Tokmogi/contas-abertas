"""Área restrita: a organização registra entradas, saídas e comprovantes."""
import csv
import io
import os
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

from flask import (
    Blueprint, Response, abort, current_app, flash, redirect, render_template,
    request, send_from_directory, url_for,
)
from flask_login import current_user, login_required

from . import db
from .models import CATEGORIAS_DESPESA, CATEGORIAS_RECEITA, Convite, Lancamento, Usuario
from .utils import hoje, ler_valor, resumo, texto_csv

bp = Blueprint("painel", __name__, url_prefix="/painel")

EXTENSOES = {"pdf", "png", "jpg", "jpeg", "webp"}
TAMANHO_MAXIMO = 5 * 1024 * 1024


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
    arquivo.stream.seek(0, os.SEEK_END)
    tamanho = arquivo.stream.tell()
    arquivo.stream.seek(0)
    if tamanho > TAMANHO_MAXIMO:
        raise ValueError("O comprovante pode ter no máximo 5 MB. Tente uma foto menor.")
    nome = f"{uuid.uuid4().hex}.{ext}"
    arquivo.save(os.path.join(current_app.config["UPLOAD_FOLDER"], nome))
    return nome


FILTROS_TIPO = {
    "receita": "Só entradas",
    "despesa": "Só saídas",
    "pendente": "Saídas sem comprovante",
}


@bp.route("/")
@login_required
def inicio():
    todos = _lancamentos_da_org().order_by(Lancamento.data.desc(), Lancamento.id.desc()).all()
    meses = sorted({l.data.strftime("%Y-%m") for l in todos}, reverse=True)

    mes = request.args.get("mes", "")
    tipo = request.args.get("tipo", "")
    do_mes = [l for l in todos if l.data.strftime("%Y-%m") == mes] if mes in meses else todos
    if tipo == "pendente":
        lista = [l for l in do_mes if l.tipo == "despesa" and not l.comprovante]
    elif tipo in ("receita", "despesa"):
        lista = [l for l in do_mes if l.tipo == tipo]
    else:
        lista = do_mes

    return render_template(
        "painel/inicio.html", lancamentos=lista, resumo=resumo(do_mes), tem_lancamentos=bool(todos),
        meses=meses, mes=mes if mes in meses else "", tipo=tipo if tipo in FILTROS_TIPO else "",
        filtros_tipo=FILTROS_TIPO,
        pendentes=sum(1 for l in todos if l.tipo == "despesa" and not l.comprovante),
    )


def _apagar_arquivo(nome: str | None) -> None:
    if nome:
        caminho = os.path.join(current_app.config["UPLOAD_FOLDER"], nome)
        if os.path.isfile(caminho):
            os.remove(caminho)


def _render_formulario(lanc, form=None, status=200):
    """form = dados enviados (após erro); sem form, mostra o lançamento salvo ou um novo em branco."""
    if form is not None:
        v = {k: form.get(k, "") for k in ("tipo", "categoria", "descricao", "valor", "data")}
    elif lanc:
        v = {"tipo": lanc.tipo, "categoria": lanc.categoria, "descricao": lanc.descricao,
             "valor": f"{lanc.valor:.2f}".replace(".", ","), "data": lanc.data.isoformat()}
    else:
        v = {"tipo": request.args.get("tipo", ""), "categoria": "", "descricao": "", "valor": "", "data": ""}
    if v["tipo"] not in ("receita", "despesa"):
        v["tipo"] = "despesa"
    return render_template(
        "painel/formulario.html", lanc=lanc, v=v, tipo=v["tipo"],
        receitas=CATEGORIAS_RECEITA, despesas=CATEGORIAS_DESPESA,
    ), status


@bp.route("/lancamentos/novo", methods=["GET", "POST"])
@bp.route("/lancamentos/<int:lanc_id>/editar", methods=["GET", "POST"])
@login_required
def formulario(lanc_id: int | None = None):
    lanc = _lancamento_ou_404(lanc_id) if lanc_id is not None else None

    if request.method == "POST":
        f = request.form
        try:
            tipo = f.get("tipo")
            if tipo not in ("receita", "despesa"):
                raise ValueError("Escolha se é entrada ou saída.")
            categorias = CATEGORIAS_RECEITA if tipo == "receita" else CATEGORIAS_DESPESA
            if f.get("categoria") not in categorias:
                raise ValueError("Escolha uma categoria válida.")
            descricao = f.get("descricao", "").strip()[:200]
            if not descricao:
                raise ValueError("Informe uma descrição.")
            valor = ler_valor(f.get("valor"))
            try:
                data_lanc = date.fromisoformat(f.get("data")) if f.get("data") else hoje()
            except ValueError:
                raise ValueError("Data inválida.")
            comprovante = _salvar_comprovante(request.files.get("comprovante"))
        except ValueError as e:
            flash(str(e), "erro")
            return _render_formulario(lanc, f, 400)

        novo = lanc is None
        if novo:
            lanc = Lancamento(organizacao_id=current_user.organizacao_id)
            db.session.add(lanc)
        lanc.tipo, lanc.categoria, lanc.descricao = tipo, f["categoria"], descricao
        lanc.valor, lanc.data = valor, data_lanc
        arquivo_antigo = None
        if comprovante or f.get("remover_comprovante"):
            arquivo_antigo, lanc.comprovante = lanc.comprovante, comprovante
        db.session.commit()
        _apagar_arquivo(arquivo_antigo)

        aviso = "Lançamento salvo."
        if tipo == "despesa" and not lanc.comprovante:
            aviso += " Lembre de anexar o comprovante quando tiver."
        flash(aviso, "ok")
        if novo and f.get("depois") == "outro":
            return redirect(url_for("painel.formulario", tipo=tipo))
        return redirect(url_for("painel.inicio"))

    return _render_formulario(lanc)


@bp.route("/lancamentos/<int:lanc_id>/excluir", methods=["POST"])
@login_required
def excluir(lanc_id: int):
    lanc = _lancamento_ou_404(lanc_id)
    descricao, arquivo = lanc.descricao, lanc.comprovante
    db.session.delete(lanc)
    db.session.commit()
    _apagar_arquivo(arquivo)
    flash(f"Lançamento “{descricao}” excluído.", "ok")
    return redirect(url_for("painel.inicio"))


@bp.route("/comprovantes/<int:lanc_id>")
@login_required
def comprovante(lanc_id: int):
    lanc = _lancamento_ou_404(lanc_id)
    if not lanc.comprovante:
        abort(404)
    resposta = send_from_directory(current_app.config["UPLOAD_FOLDER"], lanc.comprovante)
    resposta.headers["Content-Security-Policy"] = "sandbox"  # o arquivo nunca roda scripts
    resposta.headers["Cache-Control"] = "private, no-store"
    return resposta


@bp.route("/exportar.csv")
@login_required
def exportar_csv():
    """Planilha para prestação de contas em editais (abre direto no Excel)."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(["Data", "Tipo", "Categoria", "Descrição", "Valor", "Tem comprovante"])
    for l in _lancamentos_da_org().order_by(Lancamento.data).all():
        escritor.writerow([
            l.data.strftime("%d/%m/%Y"), l.tipo, l.categoria, texto_csv(l.descricao),
            f"{l.valor:.2f}".replace(".", ","), "sim" if l.comprovante else "não",
        ])
    return Response(
        "﻿" + saida.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=prestacao-de-contas.csv"},
    )


def _data_do_filtro(nome: str) -> date | None:
    try:
        return date.fromisoformat(request.args.get(nome, ""))
    except ValueError:
        return None


@bp.route("/relatorio")
@login_required
def relatorio():
    """Relatório de prestação de contas para imprimir ou salvar em PDF (editais e convênios)."""
    inicio, fim = _data_do_filtro("inicio"), _data_do_filtro("fim")
    if inicio and fim and inicio > fim:
        inicio, fim = fim, inicio

    todos = _lancamentos_da_org().order_by(Lancamento.data, Lancamento.id).all()
    anteriores = [l for l in todos if inicio and l.data < inicio]
    periodo = [l for l in todos if (not inicio or l.data >= inicio) and (not fim or l.data <= fim)]

    saldo_inicial = sum((l.valor_assinado for l in anteriores), Decimal(0))
    receitas_por_categoria = defaultdict(Decimal)
    for l in periodo:
        if l.tipo == "receita":
            receitas_por_categoria[l.categoria] += l.valor
    dados = resumo(periodo)

    return render_template(
        "painel/relatorio.html",
        org=current_user.organizacao,
        lancamentos=periodo,
        resumo=dados,
        receitas_por_categoria=dict(sorted(receitas_por_categoria.items(), key=lambda i: -i[1])),
        saldo_inicial=saldo_inicial,
        saldo_final=saldo_inicial + dados["saldo"],
        inicio=inicio or (periodo[0].data if periodo else None),
        fim=fim or (periodo[-1].data if periodo else inicio),
        filtro_inicio=request.args.get("inicio", ""),
        filtro_fim=request.args.get("fim", ""),
        hoje=hoje(),
    )


@bp.route("/configuracoes", methods=["GET", "POST"])
@login_required
def configuracoes():
    org = current_user.organizacao
    if request.method == "POST":
        org.nome = request.form.get("nome", org.nome).strip()[:120] or org.nome
        org.causa = request.form.get("causa", "").strip()[:200]
        org.cnpj = request.form.get("cnpj", "").strip()[:18]
        org.publico = request.form.get("publico") == "on"
        db.session.commit()
        flash("Configurações salvas.", "ok")
        return redirect(url_for("painel.configuracoes"))
    return render_template("painel/configuracoes.html", org=org)


@bp.route("/equipe")
@login_required
def equipe():
    org_id = current_user.organizacao_id
    membros = Usuario.query.filter_by(organizacao_id=org_id).order_by(Usuario.nome).all()
    convites = [
        c for c in Convite.query.filter_by(organizacao_id=org_id, usado_em=None)
        .order_by(Convite.criado_em.desc()).all()
        if c.valido
    ]
    return render_template("painel/equipe.html", membros=membros, convites=convites)


@bp.route("/equipe/convidar", methods=["POST"])
@login_required
def convidar():
    db.session.add(Convite(organizacao_id=current_user.organizacao_id, criado_por_id=current_user.id))
    db.session.commit()
    flash("Convite criado! Copie o link e envie para o voluntário (por WhatsApp, por exemplo).", "ok")
    return redirect(url_for("painel.equipe"))


@bp.route("/equipe/convites/<int:conv_id>/cancelar", methods=["POST"])
@login_required
def cancelar_convite(conv_id: int):
    conv = Convite.query.filter_by(id=conv_id, organizacao_id=current_user.organizacao_id).first()
    if conv is None:
        abort(404)
    db.session.delete(conv)
    db.session.commit()
    flash("Convite cancelado.", "ok")
    return redirect(url_for("painel.equipe"))
