import re
import unicodedata
from collections import defaultdict
from decimal import Decimal, InvalidOperation


def moeda(valor) -> str:
    """Formata um número no padrão brasileiro: R$ 1.234,56."""
    valor = Decimal(valor or 0)
    sinal = "-" if valor < 0 else ""
    texto = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sinal}R$ {texto}"


def ler_valor(texto: str) -> Decimal:
    """Converte '1.234,56' ou '1234.56' em Decimal positivo. Levanta ValueError se inválido."""
    texto = (texto or "").strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(texto).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError("Valor inválido.")
    if valor <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    return valor


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
        "pct_comprovado": round(100 * com_comprovante / total_despesas) if total_despesas else 100,
    }
