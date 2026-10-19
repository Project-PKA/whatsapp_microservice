"""Textos das mensagens do bot, configuráveis por loja (ADR 0006).

Um modelo usa marcadores `{nome}`. A troca é por substituição simples, NUNCA por `str.format`:
o texto vem da loja e `str.format` deixaria um modelo acessar atributos dos valores. Marcador
desconhecido fica como está, em vez de quebrar a mensagem.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal

DEFAULT_TEMPLATES: dict[str, str] = {
    # Abertura do leilão: legenda da imagem da carta.
    "card_opened": (
        "🃏 *{card}* (#{short_code})\n"
        "Lance inicial: {initial_bid} · incremento: {min_increment}\n"
        "Encerra: {ends_at}\n"
        "Para dar lance, mande: #{short_code} valor"
    ),
    "bid_too_low": "Lance abaixo do mínimo. O menor lance agora é {min_amount}.",
    "invalid_amount": (
        "Valor inválido. Use, por exemplo: #{short_code} 50 ou #{short_code} R$ 50,00"
    ),
    "not_started": "Esse leilão ainda não começou.",
    "ended": "Esse leilão já encerrou.",
    "not_active": "Esse leilão não está recebendo lances agora.",
    "ceiling_reached": (
        "A enquete chegou ao valor máximo ({amount}). O leilão fica em validação com a loja."
    ),
    "auction_won": (
        "🏆 Parabéns {winner}! {card} (#{short_code}) por {amount}. Iremos entrar em contato."
    ),
    "auction_unsold": "O leilão de {card} (#{short_code}) encerrou sem lances.",
}

_PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")


def render(template: str, values: Mapping[str, str]) -> str:
    """Troca `{nome}` pelos valores; o que não tiver valor permanece."""
    return _PLACEHOLDER_RE.sub(lambda m: values.get(m.group(1), m.group(0)), template)


def resolve_template(key: str, overrides: Mapping[str, str] | None = None) -> str:
    """Modelo da loja se houver e não for vazio; senão o padrão."""
    custom = (overrides or {}).get(key, "").strip()
    return custom or DEFAULT_TEMPLATES[key]


def format_money(amount: Decimal) -> str:
    """`R$ 1.234,56` (real, duas casas, milhar com ponto)."""
    quantized = f"{amount.quantize(Decimal('0.01')):,.2f}"
    return "R$ " + quantized.replace(",", "X").replace(".", ",").replace("X", ".")
