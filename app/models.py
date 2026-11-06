import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from flask_login import UserMixin
from sqlalchemy import Numeric
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager
from .utils import hoje

CATEGORIAS_RECEITA = [
    "Doação de pessoa física",
    "Doação de empresa",
    "Edital / convênio",
    "Evento / bazar",
    "Outras receitas",
]
CATEGORIAS_DESPESA = [
    "Alimentação",
    "Material e insumos",
    "Aluguel e contas",
    "Pessoal e voluntários",
    "Transporte",
    "Comunicação",
    "Outras despesas",
]


class Organizacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    cnpj = db.Column(db.String(18))
    causa = db.Column(db.String(200))
    publico = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    usuarios = db.relationship("Usuario", back_populates="organizacao")
    lancamentos = db.relationship(
        "Lancamento", back_populates="organizacao", cascade="all, delete-orphan"
    )


class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(256), nullable=False)
    organizacao_id = db.Column(db.Integer, db.ForeignKey("organizacao.id"), nullable=False)
    organizacao = db.relationship("Organizacao", back_populates="usuarios")

    def definir_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def conferir_senha(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)


class Lancamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organizacao_id = db.Column(
        db.Integer, db.ForeignKey("organizacao.id"), nullable=False, index=True
    )
    tipo = db.Column(db.String(7), nullable=False)  # "receita" ou "despesa"
    data = db.Column(db.Date, nullable=False, default=hoje)
    descricao = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(60), nullable=False)
    valor = db.Column(Numeric(12, 2), nullable=False)
    comprovante = db.Column(db.String(200))  # nome do arquivo salvo
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    organizacao = db.relationship("Organizacao", back_populates="lancamentos")

    @property
    def valor_assinado(self) -> Decimal:
        return self.valor if self.tipo == "receita" else -self.valor


class Convite(db.Model):
    """Link para um voluntário entrar na equipe de uma organização."""

    VALIDADE = timedelta(days=7)

    id = db.Column(db.Integer, primary_key=True)
    organizacao_id = db.Column(db.Integer, db.ForeignKey("organizacao.id"), nullable=False, index=True)
    token = db.Column(
        db.String(64), unique=True, nullable=False, index=True,
        default=lambda: secrets.token_urlsafe(24),
    )
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    usado_em = db.Column(db.DateTime)

    organizacao = db.relationship("Organizacao")
    criado_por = db.relationship("Usuario")

    @property
    def expira_em(self) -> datetime:
        criado = self.criado_em
        if criado.tzinfo is None:  # SQLite devolve datas sem fuso
            criado = criado.replace(tzinfo=timezone.utc)
        return criado + self.VALIDADE

    @property
    def valido(self) -> bool:
        return self.usado_em is None and datetime.now(timezone.utc) < self.expira_em


@login_manager.user_loader
def carregar_usuario(user_id: str):
    return db.session.get(Usuario, int(user_id))
