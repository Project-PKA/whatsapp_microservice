from decimal import Decimal

import pytest

from pokemon_bot.reactions import ACCEPTED_EMOJI, BidOutcome, Reaction, react_to_outcome
from pokemon_bot.templates import DEFAULT_TEMPLATES

AMOUNT = Decimal("50")


def _react(
    outcome: str, *, min_amount: Decimal | None = None, ceiling_reached: bool = False
) -> Reaction:
    result = BidOutcome(outcome, min_amount=min_amount, ceiling_reached=ceiling_reached)
    return react_to_outcome(result, short_code="A41", amount=AMOUNT)


def test_aceito_reage_com_emoji() -> None:
    r = _react("ACCEPTED")
    assert (r.action, r.emoji, r.notify_ceiling, r.anomaly) == (
        "react",
        ACCEPTED_EMOJI,
        False,
        False,
    )


def test_aceito_no_teto_avisa_o_grupo() -> None:
    r = _react("ACCEPTED", ceiling_reached=True)
    assert r.action == "react" and r.notify_ceiling
    assert r.template_key == "ceiling_reached" and r.params["amount"] == "R$ 50,00"


def test_lance_baixo_informa_o_minimo() -> None:
    r = _react("BID_TOO_LOW", min_amount=Decimal("55.5"))
    assert (r.action, r.template_key) == ("reply", "bid_too_low")
    assert r.params == {"min_amount": "R$ 55,50"}


def test_lance_baixo_sem_minimo_e_anomalia() -> None:
    assert _react("BID_TOO_LOW").anomaly


@pytest.mark.parametrize(
    ("outcome", "key"),
    [
        ("NOT_STARTED", "not_started"),
        ("ENDED", "ended"),
        ("AUCTION_NOT_ACTIVE", "not_active"),
        ("INVALID_AMOUNT", "invalid_amount"),
    ],
)
def test_respostas_simples(outcome: str, key: str) -> None:
    r = _react(outcome)
    assert (r.action, r.template_key) == ("reply", key)
    assert key in DEFAULT_TEMPLATES


@pytest.mark.parametrize("outcome", ["AUCTION_NOT_FOUND", "CUSTOMER_BLACKLISTED"])
def test_silencio_de_proposito(outcome: str) -> None:
    r = _react(outcome)
    assert (r.action, r.anomaly) == ("none", False)


@pytest.mark.parametrize("outcome", ["CUSTOMER_NOT_FOUND", "ALGO_NOVO", ""])
def test_anomalia_fica_em_silencio_e_sinaliza(outcome: str) -> None:
    r = _react(outcome)
    assert (r.action, r.anomaly) == ("none", True)


def test_todo_template_usado_existe() -> None:
    assert _react("ACCEPTED", ceiling_reached=True).template_key in DEFAULT_TEMPLATES
    assert _react("BID_TOO_LOW", min_amount=AMOUNT).template_key in DEFAULT_TEMPLATES
