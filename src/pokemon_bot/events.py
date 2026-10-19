"""Evento de mensagem neutro, independente do neonize (o gatilho converte para ele)."""

from __future__ import annotations

from dataclasses import dataclass

from pokemon_bot.parser import ParsedBid, parse_bid
from pokemon_bot.participant import Address


@dataclass(frozen=True)
class IncomingMessage:
    message_id: str
    is_group: bool
    is_from_me: bool
    is_edit: bool
    text: str
    sender: Address | None = None
    sender_alt: Address | None = None
    display_name: str | None = None
    # JID do grupo (`id@g.us`) e do remetente como veio, para responder e reagir à mensagem.
    chat: str | None = None
    sender_jid: str | None = None


def bid_from_message(message: IncomingMessage) -> ParsedBid | None:
    """O lance da mensagem, ou `None` se ela não deve virar lance.

    Ignora o que o próprio bot mandou, o que não veio de grupo e **mensagens editadas**: a edição
    não desfaz um lance já registrado e deixaria reescrever o valor depois do fato. Quem quer mudar
    o lance manda outra mensagem.
    """
    if message.is_from_me or not message.is_group or message.is_edit:
        return None
    return parse_bid(message.text)
