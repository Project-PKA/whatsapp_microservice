import pytest

from pokemon_bot.participant import (
    Address,
    Participant,
    Unresolved,
    clean_display_name,
    identify_participant,
    normalize_phone,
    visitor_name,
)

PN = "s.whatsapp.net"


def _never(_: Address) -> Address | None:
    raise AssertionError("não devia resolver LID")


@pytest.mark.parametrize(
    ("user", "expected"),
    [
        ("5511987654321", "5511987654321"),
        ("5511987654321:69", "5511987654321"),  # sufixo de dispositivo
        ("5511987654321_1:12", "5511987654321"),  # agente e dispositivo
        ("12345678", "12345678"),
        ("1234567", None),  # curto
        ("1234567890123456", None),  # longo
        ("0551198765", None),  # zero à esquerda
        ("55abc", None),
        ("", None),
    ],
)
def test_normalize_phone(user: str, expected: str | None) -> None:
    assert normalize_phone(Address(user, PN)) == expected


def test_normalize_phone_recusa_servidor_que_nao_e_telefone() -> None:
    assert normalize_phone(Address("5511987654321", "lid")) is None
    assert normalize_phone(Address("5511987654321", "g.us")) is None


def test_sender_com_telefone() -> None:
    result = identify_participant(Address("5511987654321:7", PN), None, "Ash", _never)
    assert result == Participant("5511987654321", "Ash")


def test_sender_lid_e_alt_com_telefone() -> None:
    result = identify_participant(
        Address("219807853060204", "lid"), Address("5511987654321", PN), "Ash", _never
    )
    assert result == Participant("5511987654321", "Ash")


def test_sender_lid_resolvido_pela_busca() -> None:
    lid = Address("219807853060204", "lid")
    result = identify_participant(
        lid, None, None, lambda a: Address("5511987654321", PN) if a == lid else None
    )
    assert result == Participant("5511987654321", "Visitante 4321")


def test_lid_alt_tambem_tenta_resolver() -> None:
    sender = Address("111", "lid")
    alt = Address("222", "lid")
    seen: list[Address] = []

    def resolve(a: Address) -> Address | None:
        seen.append(a)
        return Address("5511987654321", PN) if a == alt else None

    result = identify_participant(sender, alt, "Ash", resolve)
    assert result == Participant("5511987654321", "Ash")
    assert seen == [sender, alt]


def test_lid_nao_resolvido() -> None:
    result = identify_participant(Address("111", "lid"), None, "Ash", lambda _: None)
    assert result == Unresolved("lid_unresolved")


def test_resolucao_que_lanca_excecao_vira_nao_resolvido() -> None:
    def boom(_: Address) -> Address | None:
        raise RuntimeError("falha no store")

    result = identify_participant(Address("111", "lid"), None, None, boom)
    assert result == Unresolved("lid_unresolved")


def test_resolucao_devolve_telefone_invalido() -> None:
    result = identify_participant(Address("111", "lid"), None, None, lambda _: Address("12", PN))
    assert result == Unresolved("lid_unresolved")


def test_sem_remetente() -> None:
    assert identify_participant(None, None, "Ash", _never) == Unresolved("missing")
    assert identify_participant(Address("", PN), None, "Ash", _never) == Unresolved("missing")


def test_remetente_invalido_sem_lid() -> None:
    assert identify_participant(Address("abc", PN), None, None, _never) == Unresolved("invalid")


def test_nome_limpo() -> None:
    assert clean_display_name("  Ash\u200b   Ketchum\n") == "Ash Ketchum"
    assert clean_display_name("\u202eAsh") == "Ash"
    assert clean_display_name("   ") is None
    assert clean_display_name(None) is None
    assert len(clean_display_name("x" * 500) or "") == 100


def test_nome_do_visitante_sem_nome_de_exibicao() -> None:
    assert visitor_name("5511987654321", None) == "Visitante 4321"
    assert visitor_name("5511987654321", "  ") == "Visitante 4321"
