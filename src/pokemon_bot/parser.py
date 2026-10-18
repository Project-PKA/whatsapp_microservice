"""Parser de lance: "#A41 50", "#A41 R$ 50,00". CONTRATO entre Backend e bot (ADR 0003).

Regras:

- Só conta a mensagem inteira no formato `#<short_code> <valor>`. Qualquer texto antes ou depois
  (conversa, "por favor", emoji) faz a mensagem ser ignorada: errar para o lado de NÃO registrar
  lance é mais seguro que registrar um valor que a pessoa não quis dar.
- `short_code`: 1 a 12 letras ou dígitos, sem o `#` (o `#` é só o prefixo). A caixa é preservada;
  quem resolve o leilão decide como comparar (a restrição do banco aceita `A41` e `a41`).
- Valor, com `R$` opcional (qualquer caixa, espaço opcional depois):
  - `50`, `50,5`, `50.50`, `1.234,56`, `1,234.56`, `1.234`, `1234,56`;
  - com os dois separadores, o ÚLTIMO é o decimal;
  - um separador repetido é de milhar (grupos de 3 dígitos);
  - um separador só, seguido de exatamente 3 dígitos, é de milhar (`1.234` = 1234; leitura
    brasileira). Exceção: `0,500` é decimal;
  - mais de 2 casas decimais é devolvido como veio: o banco responde `INVALID_AMOUNT`.
- O parser não decide se o valor é aceitável (zero, mínimo, teto): isso é do `place_bid`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

MAX_MESSAGE_LENGTH = 200

# Caracteres invisíveis que o WhatsApp e os teclados costumam inserir.
_INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u200e\u200f\u2060\ufeff"))

_BID_RE = re.compile(
    r"#(?P<code>[A-Za-z0-9]{1,12})\s+(?:R\s*\$\s*)?(?P<amount>[0-9]+(?:[.,][0-9]+)*)",
    re.IGNORECASE,
)
_SEPARATOR_RE = re.compile(r"[.,]")
_MAX_AMOUNT_CHARS = 20


@dataclass(frozen=True)
class ParsedBid:
    short_code: str
    amount: Decimal


def parse_bid(text: str) -> ParsedBid | None:
    """Devolve o lance da mensagem, ou `None` se ela não for um lance."""
    cleaned = text.translate(_INVISIBLE).replace("\u00a0", " ").strip()
    if not cleaned.startswith("#") or len(cleaned) > MAX_MESSAGE_LENGTH:
        return None
    match = _BID_RE.fullmatch(cleaned)
    if match is None:
        return None
    amount = parse_amount(match.group("amount"))
    if amount is None:
        return None
    return ParsedBid(short_code=match.group("code"), amount=amount)


def parse_amount(token: str) -> Decimal | None:
    """Converte "1.234,56" e variações em `Decimal`. `None` se o formato for ambíguo ou inválido."""
    if len(token) > _MAX_AMOUNT_CHARS:
        return None
    separators = _SEPARATOR_RE.findall(token)
    if not separators:
        return Decimal(token)
    if "." in separators and "," in separators:
        return _mixed_separators(token, separators)
    return _single_kind_separator(token, separators[0], len(separators))


def _is_thousands_groups(groups: list[str]) -> bool:
    """Primeiro grupo com 1 a 3 dígitos, sem zero à esquerda; os demais com exatamente 3."""
    first, rest = groups[0], groups[1:]
    return 1 <= len(first) <= 3 and not first.startswith("0") and all(len(g) == 3 for g in rest)


def _mixed_separators(token: str, separators: list[str]) -> Decimal | None:
    decimal_sep = separators[-1]
    thousands_sep = "." if decimal_sep == "," else ","
    # Só o último separador pode ser o decimal; todos os anteriores têm de ser o de milhar.
    if any(s != thousands_sep for s in separators[:-1]):
        return None
    integer_part, _, fraction = token.rpartition(decimal_sep)
    groups = integer_part.split(thousands_sep)
    if not _is_thousands_groups(groups):
        return None
    return Decimal("".join(groups) + "." + fraction)


def _single_kind_separator(token: str, separator: str, count: int) -> Decimal | None:
    groups = token.split(separator)
    if count > 1:
        return Decimal("".join(groups)) if _is_thousands_groups(groups) else None
    integer_part, fraction = groups
    if len(fraction) == 3 and _is_thousands_groups(groups):
        return Decimal(integer_part + fraction)
    return Decimal(integer_part + "." + fraction)
