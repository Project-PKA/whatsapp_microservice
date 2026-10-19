"""Contratos entre o ciclo do bot e o cliente de WhatsApp (neonize fica atrás de `ClientHandle`)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pokemon_bot.events import IncomingMessage
from pokemon_bot.participant import Address


class SessionEvents(Protocol):
    """O que o cliente avisa. Quem implementa NUNCA deixa uma exceção sair."""

    def on_qr(self, data: bytes) -> None: ...
    def on_connected(self) -> None: ...
    def on_disconnected(self) -> None: ...
    def on_logged_out(self) -> None: ...
    def on_message(self, message: IncomingMessage) -> None: ...


class ClientHandle(Protocol):
    """Uma conexão WhatsApp de uma loja."""

    def run(self, events: SessionEvents) -> None:
        """Registra os eventos e BLOQUEIA até a conexão acabar."""
        ...

    def stop(self) -> None: ...

    def send_text(self, chat: str, text: str) -> None:
        """Texto no chat (grupo). `@número` no texto marca a pessoa."""
        ...

    def send_image(self, chat: str, path: str, caption: str) -> None: ...

    def react(self, chat: str, sender: str, message_id: str, emoji: str) -> None: ...

    def resolve_lid(self, lid: Address) -> Address | None:
        """LID -> telefone, ou `None` se não souber."""
        ...


class StatusReporter(Protocol):
    def report(self, store_id: UUID, status: str) -> None:
        """`status` é um valor de `whatsapp_status`: ONLINE, OFFLINE ou QR_READY."""
        ...


class QrSink(Protocol):
    def publish(self, store_id: UUID, data: bytes) -> None:
        """Entrega o QR para quem vai mostrá-lo (por enquanto não há canal definido)."""
        ...
