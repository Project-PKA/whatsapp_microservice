"""Converte o evento do neonize no `IncomingMessage` neutro. Só lê atributos: testável com fakes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pokemon_bot.events import IncomingMessage
from pokemon_bot.participant import Address


def jid_to_address(jid: Any, non_ad: Callable[[Any], Any]) -> Address | None:
    """JID sem sufixo de agente e de dispositivo (`JIDToNonAD`); `None` se estiver vazio."""
    if jid is None or not getattr(jid, "User", ""):
        return None
    clean = non_ad(jid)
    return Address(user=str(clean.User), server=str(clean.Server))


def _jid_string(jid: Any) -> str | None:
    """`usuario@servidor` como veio (a reação precisa do JID original do remetente)."""
    if jid is None or not getattr(jid, "User", ""):
        return None
    return f"{jid.User}@{jid.Server}"


def message_text(message: Any) -> str:
    """Texto da mensagem: `conversation` ou o texto estendido (resposta, link)."""
    return str(message.conversation or message.extendedTextMessage.text or "")


def to_incoming(event: Any, non_ad: Callable[[Any], Any]) -> IncomingMessage:
    info = event.Info
    source = info.MessageSource
    message = event.Message
    # Edição e revogação chegam marcadas em `Info.Edit` ou como mensagem de protocolo.
    is_edit = bool(info.Edit) or message.HasField("protocolMessage")
    return IncomingMessage(
        message_id=str(info.ID),
        is_group=bool(source.IsGroup),
        is_from_me=bool(source.IsFromMe),
        is_edit=is_edit,
        text=message_text(message),
        sender=jid_to_address(source.Sender, non_ad),
        sender_alt=jid_to_address(source.SenderAlt, non_ad),
        display_name=str(info.Pushname) or None,
        chat=_jid_string(source.Chat),
        sender_jid=_jid_string(source.Sender),
    )
