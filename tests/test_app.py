import io
from decimal import Decimal

import pytest

from app import criar_app, db
from app.models import Lancamento
from app.utils import ler_valor, moeda


@pytest.fixture
def app(tmp_path):
    app = criar_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "UPLOAD_FOLDER": str(tmp_path),
    })
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def cadastrar(client, org="Sopão Solidário", email="ana@exemplo.org"):
    return client.post("/cadastro", data={
        "organizacao": org, "nome": "Ana", "email": email, "senha": "senha-segura",
        "causa": "Refeições para pessoas em situação de rua",
    }, follow_redirects=True)


def lancar(client, **dados):
    base = {"tipo": "despesa", "categoria": "Alimentação", "descricao": "Arroz e feijão",
            "valor": "150,00", "data": "2026-10-05"}
    base.update(dados)
    return client.post("/painel/lancamentos/novo", data=base,
                       content_type="multipart/form-data", follow_redirects=True)


def test_formatacao_de_moeda():
    assert moeda(Decimal("1234.5")) == "R$ 1.234,50"
    assert moeda(Decimal("-10")) == "-R$ 10,00"


def test_leitura_de_valor():
    assert ler_valor("1.234,56") == Decimal("1234.56")
    assert ler_valor("99.9") == Decimal("99.90")
    with pytest.raises(ValueError):
        ler_valor("abc")
    with pytest.raises(ValueError):
        ler_valor("0")


def test_cadastro_e_lancamento(client, app):
    assert "Organização cadastrada" in cadastrar(client).get_data(as_text=True)
    lancar(client, tipo="receita", categoria="Doação de pessoa física",
           descricao="Doação mensal", valor="500")
    resposta = lancar(client)
    html = resposta.get_data(as_text=True)
    assert "R$ 350,00" in html  # saldo 500 - 150
    with app.app_context():
        assert Lancamento.query.count() == 2


def test_portal_publico_mostra_movimentacoes(client):
    cadastrar(client)
    lancar(client)
    client.get("/sair")
    html = client.get("/transparencia/sopao-solidario").get_data(as_text=True)
    assert "Arroz e feijão" in html
    assert "pendente" in html  # despesa sem comprovante fica sinalizada


def test_portal_privado_nao_aparece(client):
    cadastrar(client)
    client.post("/painel/configuracoes", data={"nome": "Sopão Solidário"})  # sem "publico"
    client.get("/sair")
    assert client.get("/transparencia/sopao-solidario").status_code == 404


def test_upload_de_comprovante(client):
    cadastrar(client)
    lancar(client, comprovante=(io.BytesIO(b"%PDF-1.4"), "nota.pdf"))
    html = client.get("/painel/").get_data(as_text=True)
    assert "ver</a>" in html


def test_comprovante_com_extensao_invalida(client):
    cadastrar(client)
    resposta = lancar(client, comprovante=(io.BytesIO(b"x"), "virus.exe"))
    assert resposta.status_code == 400


def test_organizacoes_isoladas(client, app):
    cadastrar(client)
    lancar(client)
    client.get("/sair")
    cadastrar(client, org="Outra ONG", email="bia@exemplo.org")
    with app.app_context():
        lanc_id = Lancamento.query.first().id
    assert client.get(f"/painel/lancamentos/{lanc_id}/editar").status_code == 404
    assert client.post(f"/painel/lancamentos/{lanc_id}/excluir").status_code == 404


def test_exportacao_csv(client):
    cadastrar(client)
    lancar(client)
    resposta = client.get("/painel/exportar.csv")
    assert resposta.mimetype == "text/csv"
    assert "Arroz e feijão;150,00" in resposta.get_data(as_text=True)


def test_painel_exige_login(client):
    assert client.get("/painel/").status_code == 302
