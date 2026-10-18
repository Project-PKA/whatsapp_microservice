from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pokemon_bot.parser import ParsedBid, parse_amount, parse_bid

D = Decimal


@pytest.mark.parametrize(
    ("text", "code", "amount"),
    [
        ("#A41 50", "A41", D("50")),
        ("#A41 R$ 50,00", "A41", D("50.00")),
        ("#A41 R$50", "A41", D("50")),
        ("#A41 r$ 50", "A41", D("50")),
        ("#A41 R $ 50", "A41", D("50")),
        ("#a41 50", "a41", D("50")),
        ("#A41    50", "A41", D("50")),
        ("  #A41 50  ", "A41", D("50")),
        ("#A41\t50", "A41", D("50")),
        ("#A41 50,5", "A41", D("50.5")),
        ("#A41 50.5", "A41", D("50.5")),
        ("#A41 50.50", "A41", D("50.50")),
        ("#A41 1.234,56", "A41", D("1234.56")),
        ("#A41 1,234.56", "A41", D("1234.56")),
        ("#A41 1234,56", "A41", D("1234.56")),
        ("#A41 1.234", "A41", D("1234")),
        ("#A41 1,234", "A41", D("1234")),
        ("#A41 1.234.567", "A41", D("1234567")),
        ("#A41 1,234,567.89", "A41", D("1234567.89")),
        ("#A41 0,5", "A41", D("0.5")),
        ("#A41 007", "A41", D("7")),
        ("#A41 0", "A41", D("0")),
        ("#X 10", "X", D("10")),
        ("#ABCDEFGHIJKL 10", "ABCDEFGHIJKL", D("10")),
        # NBSP e caracteres invisíveis que o teclado insere.
        ("#A41\u00a050", "A41", D("50")),
        ("\u200b#A41 50", "A41", D("50")),
        ("#A41 50\u200b", "A41", D("50")),
        # Mais de 2 casas: o parser devolve como veio; o banco responde INVALID_AMOUNT.
        ("#A41 50,555555", "A41", D("50.555555")),
        ("#A41 0,005", "A41", D("0.005")),
        ("#A41 1234.567", "A41", D("1234.567")),
    ],
)
def test_lances_validos(text: str, code: str, amount: Decimal) -> None:
    assert parse_bid(text) == ParsedBid(code, amount)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "oi pessoal",
        "A41 50",  # sem #
        "# A41 50",  # espaço depois do #
        "#A41",  # sem valor
        "#A41 ",
        "#A41 R$",
        "#A41 abc",
        "#A41 50 por favor",  # texto depois: ignora
        "bom dia #A41 50",  # texto antes: ignora
        "*#A41 50*",  # formatação do WhatsApp
        "#A41: 50",
        "#A4150",  # sem separador
        "#A41 -50",
        "#A41 +50",
        "#A41 50,",
        "#A41 ,50",
        "#A41 .50",
        "#A41 50..00",
        "#A41 1.2.3",
        "#A41 1.234,567,89",
        "#A41 1,234,56",
        "#A41 12.34.567",
        "#A41 0.123.456",
        "#A41 5e3",
        "#A41 50 60",
        "#A41 R$ R$ 50",
        "#A41 US$ 50",
        "#A41 \u0665\u0660",  # dígitos árabes
        "#A41 \uff15\uff10",  # dígitos de largura total
        "#ABCDEFGHIJKLM 10",  # 13 caracteres
        "#A_1 10",
        "#Á41 10",
        "##A41 10",
        "#A41 " + "9" * 21,
        "#A41 50\n#A42 60",  # duas linhas
        "#" + "A" * 300 + " 1",
    ],
)
def test_nao_e_lance(text: str) -> None:
    assert parse_bid(text) is None


def test_numero_enorme_dentro_do_limite_e_devolvido_para_o_banco_recusar() -> None:
    assert parse_bid("#A41 " + "9" * 20) == ParsedBid("A41", D("9" * 20))


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("100", D("100")),
        ("100,00", D("100.00")),
        ("100.00", D("100.00")),
        ("999.999", D("999999")),
        ("1.000", D("1000")),
        ("0.500", D("0.500")),
        ("01.234", D("1.234")),  # zero à esquerda não é milhar
        ("1.234,5", D("1234.5")),
        ("12.345,67", D("12345.67")),
        ("123.456,78", D("123456.78")),
        ("1.234.567,89", D("1234567.89")),
    ],
)
def test_parse_amount(token: str, expected: Decimal) -> None:
    assert parse_amount(token) == expected


@pytest.mark.parametrize("token", ["1.2.3", "1,2.3", "1.234,5,6", "1234.567,89", "0.123,45"])
def test_parse_amount_ambiguo_ou_invalido(token: str) -> None:
    assert parse_amount(token) is None


@given(
    cents=st.integers(min_value=1, max_value=9_999_999_999),
    decimal_sep=st.sampled_from([",", "."]),
    prefix=st.sampled_from(["", "R$", "R$ ", "r$ "]),
    pad=st.sampled_from(["", "  "]),
)
def test_propriedade_valor_com_duas_casas_volta_igual(
    cents: int, decimal_sep: str, prefix: str, pad: str
) -> None:
    integer, frac = divmod(cents, 100)
    text = f"#K9{pad} {prefix}{integer}{decimal_sep}{frac:02d}"
    # Só vale quando a parte inteira não vira "milhar" por acaso (ex.: "1.234" não aparece aqui,
    # porque sempre há duas casas decimais depois do separador).
    assert parse_bid(text) == ParsedBid("K9", D(cents) / 100)


@given(cents=st.integers(min_value=100_000, max_value=9_999_999_999), brazilian=st.booleans())
def test_propriedade_valor_com_milhar(cents: int, brazilian: bool) -> None:
    integer, frac = divmod(cents, 100)
    thousands, decimal = (".", ",") if brazilian else (",", ".")
    grouped = f"{integer:,}".replace(",", thousands)
    assert parse_bid(f"#K9 {grouped}{decimal}{frac:02d}") == ParsedBid("K9", D(cents) / 100)


@given(st.text(max_size=300))
def test_nunca_lanca_excecao(text: str) -> None:
    result = parse_bid(text)
    assert result is None or (result.amount >= 0 and result.short_code.isalnum())
