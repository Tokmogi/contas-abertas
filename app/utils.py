import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")


def hoje() -> date:
    """Data de hoje no horário de Brasília (o servidor costuma rodar em UTC)."""
    return datetime.now(FUSO).date()


def no_fuso(momento: datetime) -> datetime:
    """Converte um horário salvo em UTC para o horário de Brasília."""
    if momento.tzinfo is None:  # SQLite devolve sem fuso; salvamos sempre em UTC
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(FUSO)


def moeda(valor) -> str:
    """Formata um número no padrão brasileiro: R$ 1.234,56."""
    valor = Decimal(valor or 0)
    sinal = "-" if valor < 0 else ""
    texto = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sinal}R$ {texto}"


VALOR_MAXIMO = Decimal("9999999999.99")  # cabe na coluna Numeric(12, 2)


def ler_valor(texto: str) -> Decimal:
    """Converte '1.234,56', '1.500' ou '1234.56' em Decimal positivo. Levanta ValueError se inválido."""
    texto = (texto or "").strip().replace("R$", "").replace(" ", "")
    if not re.fullmatch(r"[\d.,]+", texto):
        raise ValueError("Valor inválido. Use só números, como 150,00.")
    if "," in texto:
        inteiro, _, centavos = texto.rpartition(",")
        if "," in inteiro:
            raise ValueError("Valor inválido. Use só números, como 150,00.")
        texto = inteiro.replace(".", "") + "." + centavos
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", texto):
        texto = texto.replace(".", "")  # "1.500" é mil e quinhentos (ponto de milhar)
    try:
        valor = Decimal(texto).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError("Valor inválido. Use só números, como 150,00.")
    if valor <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    if valor > VALOR_MAXIMO:
        raise ValueError("Valor alto demais. Confira se digitou certo.")
    return valor


def texto_csv(valor: str) -> str:
    """Evita que o Excel interprete o texto como fórmula (ex.: '=HYPERLINK(...)')."""
    return "'" + valor if valor[:1] in ("=", "+", "-", "@", "\t", "\r") else valor


MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MESES_EXTENSO = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
                 "setembro", "outubro", "novembro", "dezembro"]


def mes_curto(chave: str) -> str:
    """'2026-10' -> 'out/2026'."""
    ano, mes = chave.split("-")
    return f"{MESES[int(mes) - 1]}/{ano}"


def mes_por_extenso(chave: str) -> str:
    """'2026-10' -> 'outubro de 2026'."""
    ano, mes = chave.split("-")
    return f"{MESES_EXTENSO[int(mes) - 1]} de {ano}"


def gerar_slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-") or "organizacao"


def resumo(lancamentos) -> dict:
    """Totais gerais, por categoria e por mês, usados no painel e no portal público."""
    receitas = sum((l.valor for l in lancamentos if l.tipo == "receita"), Decimal(0))
    despesas = sum((l.valor for l in lancamentos if l.tipo == "despesa"), Decimal(0))

    por_categoria = defaultdict(Decimal)
    por_mes = defaultdict(lambda: {"receita": Decimal(0), "despesa": Decimal(0)})
    for l in lancamentos:
        if l.tipo == "despesa":
            por_categoria[l.categoria] += l.valor
        por_mes[l.data.strftime("%Y-%m")][l.tipo] += l.valor

    com_comprovante = sum(1 for l in lancamentos if l.tipo == "despesa" and l.comprovante)
    total_despesas = sum(1 for l in lancamentos if l.tipo == "despesa")

    return {
        "receitas": receitas,
        "despesas": despesas,
        "saldo": receitas - despesas,
        "por_categoria": dict(sorted(por_categoria.items(), key=lambda i: -i[1])),
        "por_mes": dict(sorted(por_mes.items())),
        "por_mes_rotulos": {mes_curto(k): v for k, v in sorted(por_mes.items())},
        "pct_comprovado": round(100 * com_comprovante / total_despesas) if total_despesas else None,
    }
