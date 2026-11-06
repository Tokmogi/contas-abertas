import io
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app import criar_app, db
from app.models import Convite, Lancamento, Usuario
from app.utils import ler_valor, moeda


@pytest.fixture
def app(tmp_path):
    app = criar_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "UPLOAD_FOLDER": str(tmp_path),
        "CSRF_ATIVO": False,
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


def test_csrf_bloqueia_formulario_sem_token(tmp_path):
    app = criar_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
                     "UPLOAD_FOLDER": str(tmp_path)})
    client = app.test_client()
    assert cadastrar(client).status_code == 400  # sem token: recusado

    html = client.get("/cadastro").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    resposta = client.post("/cadastro", data={
        "organizacao": "Sopão", "nome": "Ana", "email": "ana@exemplo.org",
        "senha": "senha-segura", "csrf_token": token,
    })
    assert resposta.status_code == 302  # com token: aceito


def criar_convite(client, app):
    client.post("/painel/equipe/convidar")
    with app.app_context():
        return Convite.query.order_by(Convite.id.desc()).first().token


def test_convite_de_voluntario(client, app):
    cadastrar(client)
    token = criar_convite(client, app)
    assert token in client.get("/painel/equipe").get_data(as_text=True)
    client.get("/sair")

    html = client.post(f"/convite/{token}", data={
        "nome": "Bruno", "email": "bruno@exemplo.org", "senha": "outra-senha",
    }, follow_redirects=True).get_data(as_text=True)
    assert "Bem-vindo(a) à equipe de Sopão Solidário" in html

    # o voluntário enxerga e registra lançamentos da mesma organização
    lancar(client, descricao="Panelas novas")
    with app.app_context():
        ana = Usuario.query.filter_by(email="ana@exemplo.org").first()
        bruno = Usuario.query.filter_by(email="bruno@exemplo.org").first()
        assert ana.organizacao_id == bruno.organizacao_id
        assert Lancamento.query.first().organizacao_id == ana.organizacao_id

    # o link só pode ser usado uma vez
    client.get("/sair")
    assert client.get(f"/convite/{token}").status_code == 410


def test_convite_expirado(client, app):
    cadastrar(client)
    token = criar_convite(client, app)
    with app.app_context():
        conv = Convite.query.filter_by(token=token).first()
        conv.criado_em = datetime.now(timezone.utc) - timedelta(days=8)
        db.session.commit()
    client.get("/sair")
    assert client.get(f"/convite/{token}").status_code == 410
    assert client.get("/convite/nao-existe").status_code == 404


def test_convite_de_outra_organizacao_nao_pode_ser_cancelado(client, app):
    cadastrar(client)
    criar_convite(client, app)
    client.get("/sair")
    cadastrar(client, org="Outra ONG", email="bia@exemplo.org")
    with app.app_context():
        conv_id = Convite.query.first().id
    assert client.post(f"/painel/equipe/convites/{conv_id}/cancelar").status_code == 404


def test_relatorio_por_periodo(client):
    cadastrar(client)
    lancar(client, tipo="receita", categoria="Doação de pessoa física",
           descricao="Doação de setembro", valor="1000", data="2026-09-10")
    lancar(client, descricao="Gás de setembro", valor="100", data="2026-09-20")
    lancar(client, descricao="Cestas de outubro", valor="300", data="2026-10-05")

    html = client.get("/painel/relatorio?inicio=2026-10-01&fim=2026-10-31").get_data(as_text=True)
    assert "01/10/2026 a 31/10/2026" in html
    assert "Cestas de outubro" in html
    assert "Gás de setembro" not in html
    assert "R$ 900,00" in html  # saldo inicial (1000 - 100)
    assert "R$ 600,00" in html  # saldo final (900 - 300)

    html = client.get("/painel/relatorio").get_data(as_text=True)
    assert "10/09/2026 a 05/10/2026" in html  # sem filtro: todo o período


# --- Bugs corrigidos ---------------------------------------------------------

def test_valor_com_ponto_de_milhar():
    assert ler_valor("1.500") == Decimal("1500.00")      # "mil e quinhentos", não R$ 1,50
    assert ler_valor("12.345.678") == Decimal("12345678.00")
    assert ler_valor("R$ 2.500,75") == Decimal("2500.75")
    assert ler_valor("10.5") == Decimal("10.50")
    for invalido in ["NaN", "Infinity", "1e5", "-5", "1,2,3", "9999999999999"]:
        with pytest.raises(ValueError):
            ler_valor(invalido)


def test_valor_invalido_nao_quebra_o_formulario(client):
    cadastrar(client)
    assert lancar(client, valor="NaN").status_code == 400


def test_relatorio_sem_movimentacoes_no_periodo(client):
    cadastrar(client)
    lancar(client)
    assert client.get("/painel/relatorio?inicio=2030-01-01").status_code == 200
    assert client.get("/painel/relatorio?fim=2000-01-01").status_code == 200


def test_excluir_lancamento(client, app):
    cadastrar(client)
    lancar(client)
    with app.app_context():
        lanc_id = Lancamento.query.first().id
    html = client.post(f"/painel/lancamentos/{lanc_id}/excluir", follow_redirects=True).get_data(as_text=True)
    assert "Arroz e feijão" in html and "excluído" in html
    with app.app_context():
        assert Lancamento.query.count() == 0


def test_excluir_apaga_o_arquivo_do_comprovante(client, tmp_path, app):
    cadastrar(client)
    lancar(client, comprovante=(io.BytesIO(b"%PDF-1.4"), "nota.pdf"))
    assert len(list(tmp_path.iterdir())) == 1
    with app.app_context():
        lanc_id = Lancamento.query.first().id
    client.post(f"/painel/lancamentos/{lanc_id}/excluir")
    assert list(tmp_path.iterdir()) == []


def test_csv_neutraliza_formulas(client):
    cadastrar(client)
    lancar(client, descricao="=HYPERLINK(\"http://golpe\")")
    texto = client.get("/painel/exportar.csv").get_data(as_text=True)
    assert "'=HYPERLINK" in texto and ';=HYPERLINK' not in texto


def test_textos_longos_sao_recusados_no_cadastro(client):
    resposta = client.post("/cadastro", data={
        "organizacao": "x" * 300, "nome": "Ana", "email": "ana@exemplo.org", "senha": "senha-segura",
    })
    assert resposta.status_code == 400


def test_pagina_privada_visivel_para_a_propria_equipe(client):
    cadastrar(client)
    client.post("/painel/configuracoes", data={"nome": "Sopão Solidário"})
    html = client.get("/transparencia/sopao-solidario").get_data(as_text=True)
    assert "privada" in html


def test_filtro_de_pendentes(client):
    cadastrar(client)
    lancar(client, descricao="Gasto sem nota")
    lancar(client, descricao="Gasto com nota", comprovante=(io.BytesIO(b"%PDF"), "n.pdf"))
    html = client.get("/painel/?tipo=pendente").get_data(as_text=True)
    assert "Gasto sem nota" in html and "Gasto com nota" not in html


def test_login_volta_para_a_pagina_pedida(client):
    cadastrar(client)
    client.get("/sair")
    r = client.post("/entrar?next=/painel/equipe", data={"email": "ana@exemplo.org", "senha": "senha-segura"})
    assert r.headers["Location"].endswith("/painel/equipe")
    client.get("/sair")
    r = client.post("/entrar?next=https://golpe.com", data={"email": "ana@exemplo.org", "senha": "senha-segura"})
    assert "golpe" not in r.headers["Location"]


def test_pagina_de_erro_amigavel(client):
    html = client.get("/nao-existe").get_data(as_text=True)
    assert "Página não encontrada" in html


@pytest.mark.parametrize("destino", ["/%09/golpe.com", "/%0A/golpe.com", "//golpe.com", "/\\golpe.com"])
def test_login_nao_redireciona_para_fora(client, destino):
    cadastrar(client)
    client.get("/sair")
    r = client.post(f"/entrar?next={destino}", data={"email": "ana@exemplo.org", "senha": "senha-segura"})
    assert r.status_code == 302
    assert "golpe" not in r.headers["Location"]


def test_csrf_com_token_estranho_nao_quebra(tmp_path):
    app = criar_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "UPLOAD_FOLDER": str(tmp_path)})
    client = app.test_client()
    client.get("/cadastro")
    assert client.post("/cadastro", data={"csrf_token": "é"}).status_code == 400


def test_comprovante_de_5mb_e_aceito_e_maior_e_recusado(client):
    cadastrar(client)
    cinco_mb = b"%PDF" + b"0" * (5 * 1024 * 1024 - 4)
    assert lancar(client, comprovante=(io.BytesIO(cinco_mb), "a.pdf")).status_code == 200
    resposta = lancar(client, comprovante=(io.BytesIO(cinco_mb + b"0"), "b.pdf"))
    assert resposta.status_code == 400
    assert "no máximo 5 MB" in resposta.get_data(as_text=True)


def test_comprovante_servido_com_protecoes(client):
    cadastrar(client)
    lancar(client, comprovante=(io.BytesIO(b"<html><script>alert(1)</script>"), "a.png"))
    r = client.get("/painel/comprovantes/1")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Content-Security-Policy"] == "sandbox"


def test_erro_na_edicao_mantem_o_que_foi_digitado(client):
    cadastrar(client)
    lancar(client)
    r = client.post("/painel/lancamentos/1/editar", data={
        "tipo": "despesa", "categoria": "Alimentação", "descricao": "", "valor": "99,90", "data": "2026-10-05",
    })
    html = r.get_data(as_text=True)
    assert r.status_code == 400
    assert 'value="99,90"' in html and "Arroz e feijão" not in html


def test_tipo_desconhecido_vira_saida(client):
    cadastrar(client)
    html = client.get("/painel/lancamentos/novo?tipo=foo").get_data(as_text=True)
    assert 'value="despesa" checked' in html


def test_editar_lancamento_zero_nao_cria_novo(client, app):
    cadastrar(client)
    assert lancar_em(client, "/painel/lancamentos/0/editar").status_code == 404
    with app.app_context():
        assert Lancamento.query.count() == 0


def lancar_em(client, url):
    return client.post(url, data={"tipo": "despesa", "categoria": "Alimentação", "descricao": "X",
                                  "valor": "1", "data": "2026-10-05"})


def test_sem_saidas_nao_mostra_100_por_cento_comprovado(client):
    cadastrar(client)
    lancar(client, tipo="receita", categoria="Doação de pessoa física", descricao="Doação", valor="50")
    html = client.get("/transparencia/sopao-solidario").get_data(as_text=True)
    assert "100%" not in html and "—" in html


def test_data_padrao_no_horario_de_brasilia(client, app, monkeypatch):
    from datetime import date as date_real
    import app.painel as painel
    monkeypatch.setattr(painel, "hoje", lambda: date_real(2026, 12, 31))
    cadastrar(client)
    lancar(client, data="")
    with app.app_context():
        assert Lancamento.query.first().data == date_real(2026, 12, 31)
