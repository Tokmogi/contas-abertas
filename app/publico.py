"""Portal público de transparência: qualquer pessoa vê para onde foi o dinheiro."""
from flask import Blueprint, abort, render_template

from .models import Lancamento, Organizacao
from .utils import resumo

bp = Blueprint("publico", __name__)


@bp.route("/")
def inicio():
    orgs = Organizacao.query.filter_by(publico=True).order_by(Organizacao.nome).all()
    return render_template("publico/inicio.html", orgs=orgs)


@bp.route("/transparencia/<slug>")
def transparencia(slug: str):
    org = Organizacao.query.filter_by(slug=slug, publico=True).first()
    if org is None:
        abort(404)
    lancamentos = (
        Lancamento.query.filter_by(organizacao_id=org.id)
        .order_by(Lancamento.data.desc(), Lancamento.id.desc())
        .all()
    )
    # Valores e categorias são públicos; os arquivos de comprovante, não
    # (podem conter dados pessoais — LGPD). Mostramos só se existe comprovante.
    return render_template(
        "publico/transparencia.html", org=org, lancamentos=lancamentos, resumo=resumo(lancamentos)
    )
