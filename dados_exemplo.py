"""Cria uma organização de demonstração com alguns meses de movimentação.

Uso: python dados_exemplo.py
Login: demo@contasabertas.org / demonstracao
"""
from datetime import date
from decimal import Decimal

from app import criar_app, db
from app.models import Lancamento, Organizacao, Usuario

MOVIMENTOS = [
    ("receita", "2026-08-02", "Doações do mês (Pix)", "Doação de pessoa física", "1850.00"),
    ("despesa", "2026-08-05", "Cestas básicas — 20 famílias", "Alimentação", "1240.00"),
    ("despesa", "2026-08-10", "Gás de cozinha", "Aluguel e contas", "125.00"),
    ("receita", "2026-09-01", "Doações do mês (Pix)", "Doação de pessoa física", "2100.00"),
    ("receita", "2026-09-15", "Bazar beneficente", "Evento / bazar", "860.00"),
    ("despesa", "2026-09-06", "Cestas básicas — 24 famílias", "Alimentação", "1488.00"),
    ("despesa", "2026-09-20", "Material escolar para o reforço", "Material e insumos", "430.50"),
    ("receita", "2026-10-03", "Edital Fundo Municipal da Criança", "Edital / convênio", "5000.00"),
    ("despesa", "2026-10-07", "Cestas básicas — 25 famílias", "Alimentação", "1550.00"),
    ("despesa", "2026-10-18", "Transporte para passeio educativo", "Transporte", "600.00"),
]

app = criar_app()
with app.app_context():
    if Organizacao.query.filter_by(slug="instituto-mao-amiga").first():
        print("Dados de exemplo já existem.")
    else:
        org = Organizacao(nome="Instituto Mão Amiga", slug="instituto-mao-amiga",
                          causa="Alimentação e reforço escolar para famílias da comunidade")
        usuario = Usuario(nome="Demonstração", email="demo@contasabertas.org", organizacao=org)
        usuario.definir_senha("demonstracao")
        db.session.add_all([org, usuario])
        for i, (tipo, dia, desc, cat, valor) in enumerate(MOVIMENTOS):
            db.session.add(Lancamento(
                organizacao=org, tipo=tipo, data=date.fromisoformat(dia), descricao=desc,
                categoria=cat, valor=Decimal(valor),
                comprovante="exemplo.pdf" if tipo == "despesa" and i % 3 else None,
            ))
        db.session.commit()
        print("Pronto! Acesse /transparencia/instituto-mao-amiga")
        print("Login: demo@contasabertas.org / demonstracao")
