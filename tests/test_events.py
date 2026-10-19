from decimal import Decimal

from pokemon_bot.events import IncomingMessage, bid_from_message
from pokemon_bot.parser import ParsedBid


def _msg(
    *, text: str = "#A41 50", is_group: bool = True, is_from_me: bool = False, is_edit: bool = False
) -> IncomingMessage:
    return IncomingMessage(
        message_id="m1", is_group=is_group, is_from_me=is_from_me, is_edit=is_edit, text=text
    )


def test_lance_em_grupo() -> None:
    assert bid_from_message(_msg()) == ParsedBid("A41", Decimal("50"))


def test_ignora_mensagem_editada() -> None:
    assert bid_from_message(_msg(is_edit=True)) is None


def test_ignora_mensagem_do_proprio_bot() -> None:
    assert bid_from_message(_msg(is_from_me=True)) is None


def test_ignora_conversa_privada() -> None:
    assert bid_from_message(_msg(is_group=False)) is None


def test_ignora_conversa_comum() -> None:
    assert bid_from_message(_msg(text="bom dia")) is None
