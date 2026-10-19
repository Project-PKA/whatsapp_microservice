"""Único módulo que conhece o neonize. Não foi exercitado com uma conta real nesta fase.

O que foi lido na documentação e na API do neonize 0.5.2 e AINDA precisa de teste manual com a conta
de teste (OWNER.md, A9): QR e pareamento, reconexão, `Info.Edit` nas edições, o uso de `uuid` e
`name` como banco da sessão (o README fala em `database=`, a assinatura instalada não tem), envio
de imagem com legenda e remoção de participante.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from pokemon_bot.participant import Address
from pokemon_bot.trigger.whatsapp.convert import jid_to_address, to_incoming
from pokemon_bot.trigger.whatsapp.pacing import (
    MESSAGE_PACING,
    MODERATION_PACING,
    REACTION_PACING,
    Pacer,
    PacingConfig,
)
from pokemon_bot.trigger.whatsapp.ports import GroupMember, SessionEvents


class NeonizeHandle:
    def __init__(
        self,
        session_db: str,
        store_id: UUID,
        *,
        new_device: bool = False,
        client_factory: Callable[..., Any] | None = None,
        message_pacing: PacingConfig = MESSAGE_PACING,
        reaction_pacing: PacingConfig = REACTION_PACING,
        moderation_pacing: PacingConfig = MODERATION_PACING,
    ) -> None:
        self._session_db = session_db
        self._store_id = store_id
        self._new_device = new_device
        self._client_factory = client_factory
        self._message_pacer = Pacer(message_pacing)
        self._reaction_pacer = Pacer(reaction_pacing)
        self._moderation_pacer = Pacer(moderation_pacing)
        self._client: Any = None

    # --- conexão ---------------------------------------------------------------------------------
    def run(self, events: SessionEvents) -> None:
        from neonize.client import NewClient
        from neonize.events import (
            ConnectedEv,
            DisconnectedEv,
            LoggedOutEv,
            MessageEv,
        )
        from neonize.utils.jid import JIDToNonAD

        factory = self._client_factory or NewClient
        client = factory(self._session_db, uuid=str(self._store_id), new_device=self._new_device)
        self._client = client

        # Os `events.on_*` já são blindados pela sessão; mesmo assim nada aqui lança.
        client.event.qr(lambda _c, data: events.on_qr(bytes(data)))

        @client.event(ConnectedEv)
        def _connected(_c: Any, _e: Any) -> None:
            events.on_connected()

        @client.event(DisconnectedEv)
        def _disconnected(_c: Any, _e: Any) -> None:
            events.on_disconnected()

        @client.event(LoggedOutEv)
        def _logged_out(_c: Any, _e: Any) -> None:
            events.on_logged_out()

        @client.event(MessageEv)
        def _message(_c: Any, ev: Any) -> None:
            try:
                incoming = to_incoming(ev, JIDToNonAD)
            except Exception:
                return  # evento que não sabemos ler: ignora (o tipo do erro não carrega dado útil)
            events.on_message(incoming)

        client.connect()  # bloqueia

    def stop(self) -> None:
        client = self._client
        if client is not None:
            client.stop()

    # --- envio (sempre no ritmo humano) ---
    def send_text(self, chat: str, text: str) -> None:
        self._message_pacer.wait_turn()
        self._client.send_message(self._jid(chat), text)

    def send_image(self, chat: str, path: str, caption: str) -> None:
        self._message_pacer.wait_turn()
        self._client.send_image(self._jid(chat), path, caption=caption)

    def react(self, chat: str, sender: str, message_id: str, emoji: str) -> None:
        self._reaction_pacer.wait_turn()
        message = self._client.build_reaction(self._jid(chat), self._jid(sender), message_id, emoji)
        self._client.send_message(self._jid(chat), message)

    # --- moderação (NÃO testada com conta real: docs/moderacao.md) ---
    def group_participants(self, chat: str) -> list[GroupMember]:
        info = self._client.get_group_info(self._jid(chat))
        members = []
        for p in info.Participants:
            phone_jid = p.PhoneNumber if getattr(p.PhoneNumber, "User", "") else p.JID
            phone = phone_jid.User if phone_jid.Server == "s.whatsapp.net" else None
            members.append(
                GroupMember(
                    jid=f"{p.JID.User}@{p.JID.Server}",
                    phone=phone or None,
                    is_admin=bool(p.IsAdmin or p.IsSuperAdmin),
                )
            )
        return members

    def remove_participant(self, chat: str, jid: str) -> None:
        from neonize.utils.enum import ParticipantChange

        self._moderation_pacer.wait_turn()
        self._client.update_group_participants(
            self._jid(chat), [self._jid(jid)], ParticipantChange.REMOVE
        )

    # --- identificação ---------------------------------------------------------------------------
    def resolve_lid(self, lid: Address) -> Address | None:
        """LID -> telefone, no store do whatsmeow. `None` se não souber."""
        from neonize.utils.jid import JIDToNonAD

        result = self._client.get_pn_from_lid(self._jid(f"{lid.user}@{lid.server}"))
        return jid_to_address(result, JIDToNonAD)

    @staticmethod
    def _jid(value: str) -> Any:
        from neonize.utils.jid import build_jid

        user, _, server = value.partition("@")
        return build_jid(user, server) if server else build_jid(user)
