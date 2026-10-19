from decimal import Decimal

import pytest

from pokemon_bot.templates import DEFAULT_TEMPLATES, format_money, render, resolve_template


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("50"), "R$ 50,00"),
        (Decimal("1234.5"), "R$ 1.234,50"),
        (Decimal("1234567.89"), "R$ 1.234.567,89"),
        (Decimal("0.5"), "R$ 0,50"),
    ],
)
def test_format_money(amount: Decimal, expected: str) -> None:
    assert format_money(amount) == expected


def test_render_troca_marcadores_e_mantem_os_desconhecidos() -> None:
    assert render("Oi {name}, {outro}", {"name": "Ash"}) == "Oi Ash, {outro}"


def test_render_nao_executa_acesso_a_atributos() -> None:
    assert render("{winner.__class__}", {"winner": "x"}) == "{winner.__class__}"
    assert render("{0}", {}) == "{0}"


def test_render_valor_com_chaves_nao_e_reexpandido() -> None:
    assert render("{a}", {"a": "{b}", "b": "x"}) == "{b}"


def test_template_da_loja_ou_padrao() -> None:
    assert resolve_template("ended", {"ended": "Acabou!"}) == "Acabou!"
    assert resolve_template("ended", {"ended": "  "}) == DEFAULT_TEMPLATES["ended"]
    assert resolve_template("ended", None) == DEFAULT_TEMPLATES["ended"]
    assert resolve_template("ended", {"other": "x"}) == DEFAULT_TEMPLATES["ended"]


def test_vencedor_padrao_marca_a_pessoa() -> None:
    text = render(
        DEFAULT_TEMPLATES["auction_won"],
        {"winner": "@5511987654321", "card": "Pikachu", "short_code": "A41", "amount": "R$ 50,00"},
    )
    assert "@5511987654321" in text and "Pikachu" in text and "#A41" in text
    assert "{" not in text
