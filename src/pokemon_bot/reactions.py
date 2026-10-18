"""Máquina de reações: o `outcome` de `place_bid` decide o que o bot faz no grupo (ADR 0016).

A regra de lance NÃO está aqui. Este módulo só traduz a resposta do banco em ação:
reagir à mensagem, responder com um texto, ou ficar em silêncio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from pokemon_bot.templates import format_money

ACCEPTED_EMOJI = "✅"


@dataclass(frozen=True)
class BidOutcome:
    """Espelho do que `place_bid` devolve (as colunas que o bot usa)."""

    outcome: str
    min_amount: Decimal | None = None
    current_amount: Decimal | None = None
    ceiling_reached: bool = False


@dataclass(frozen=True)
class Reaction:
    action: Literal["react", "reply", "none"]
    emoji: str | None = None
    template_key: str | None = None
    params: dict[str, str] = field(default_factory=dict)
    # Situação que não deveria acontecer: o chamador registra um aviso (sem dado pessoal).
    anomaly: bool = False
    # O leilão chegou ao teto e foi para validação: o chamador também avisa o grupo.
    notify_ceiling: bool = False


SILENT = Reaction("none")


def _reply(key: str, **params: str) -> Reaction:
    return Reaction("reply", template_key=key, params=params)


def react_to_outcome(result: BidOutcome, *, short_code: str, amount: Decimal) -> Reaction:
    """Traduz o resultado de `place_bid` em ação no grupo.

    Silêncio de propósito:
    - `AUCTION_NOT_FOUND`: "#12 50" pode ser conversa comum; responder viraria spam.
    - `CUSTOMER_BLACKLISTED`: não expor a moderação no grupo.
    Anomalia (silêncio e aviso): `CUSTOMER_NOT_FOUND` (o Visitante é criado antes do lance) e
    qualquer `outcome` desconhecido (o banco ganhou um resultado novo que o bot ainda não conhece).
    """
    outcome = result.outcome
    if outcome == "ACCEPTED":
        if result.ceiling_reached:
            return Reaction(
                "react",
                emoji=ACCEPTED_EMOJI,
                template_key="ceiling_reached",
                params={"amount": format_money(amount), "short_code": short_code},
                notify_ceiling=True,
            )
        return Reaction("react", emoji=ACCEPTED_EMOJI)
    if outcome == "BID_TOO_LOW":
        if result.min_amount is None:
            return Reaction("none", anomaly=True)
        return _reply("bid_too_low", min_amount=format_money(result.min_amount))
    if outcome == "INVALID_AMOUNT":
        return _reply("invalid_amount", short_code=short_code)
    simple = {
        "NOT_STARTED": "not_started",
        "ENDED": "ended",
        "AUCTION_NOT_ACTIVE": "not_active",
    }
    if outcome in simple:
        return _reply(simple[outcome])
    if outcome in ("AUCTION_NOT_FOUND", "CUSTOMER_BLACKLISTED"):
        return SILENT
    return Reaction("none", anomaly=True)
