"""Do evento do grupo ao lance registrado e à reação (ADR 0003, 0005 e 0016).

Ordem: ler o lance, identificar o participante, achar (ou criar) o Visitante, achar o leilão pelo
`#ID`, chamar `place_bid` do banco e responder conforme o `outcome`. A regra do lance é do banco.

Nada daqui registra telefone, nome ou texto da mensagem: só ids internos e o tipo do resultado.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Mapping
from decimal import Decimal
from uuid import UUID

from pokemon_bot import repository
from pokemon_bot.db import Database
from pokemon_bot.events import IncomingMessage, bid_from_message
from pokemon_bot.participant import Participant, identify_participant
from pokemon_bot.reactions import BidOutcome, Reaction, react_to_outcome
from pokemon_bot.templates import render, resolve_template
from pokemon_bot.trigger.whatsapp.ports import ClientHandle

TemplatesFor = Callable[[UUID], Mapping[str, str] | None]


class GroupDirectory:
    """Grupo de WhatsApp de cada loja (`stores.whatsapp_group_id`), com cache curto."""

    def __init__(
        self, db: Database, *, ttl: float = 30.0, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._db = db
        self._ttl = ttl
        self._clock = clock
        self._lock = threading.Lock()
        self._groups: dict[UUID, str | None] = {}
        self._loaded_at: float | None = None

    def group_of(self, store_id: UUID) -> str | None:
        with self._lock:
            fresh = self._loaded_at is not None and self._clock() - self._loaded_at < self._ttl
            if not fresh:
                with self._db.platform_transaction() as conn:
                    stores = repository.list_stores(conn)
                self._groups = {s.id: s.whatsapp_group_id for s in stores}
                self._loaded_at = self._clock()
            return self._groups.get(store_id)


class BidProcessor:
    def __init__(
        self,
        db: Database,
        groups: GroupDirectory,
        logger: logging.Logger,
        templates_for: TemplatesFor = lambda _store: None,
    ) -> None:
        self._db = db
        self._groups = groups
        self._log = logger
        self._templates_for = templates_for

    def handle(self, store_id: UUID, message: IncomingMessage, client: ClientHandle) -> None:
        """Trata uma mensagem do WhatsApp. Chamado dentro do handler blindado da sessão."""
        bid = bid_from_message(message)
        if bid is None or message.chat is None:
            return
        if message.chat != self._groups.group_of(store_id):
            return  # outro grupo (ou a loja ainda não escolheu o dela)

        participant = identify_participant(
            message.sender, message.sender_alt, message.display_name, client.resolve_lid
        )
        if not isinstance(participant, Participant):
            # O fato, sem o LID (dado pessoal): o participante não pode virar cliente sem telefone.
            self._log.warning(
                "participante sem telefone",
                extra={"context": {"store_id": str(store_id), "reason": participant.reason}},
            )
            return

        with self._db.store_transaction(store_id) as conn:
            auction = repository.find_auction_by_short_code(conn, store_id, bid.short_code)
            if auction is None:
                return
            customer = repository.find_or_create_visitor(
                conn, store_id, participant.phone, participant.name
            )
            outcome = repository.place_bid(
                conn,
                store_id=store_id,
                auction_id=auction.auction_id,
                customer_id=customer.id,
                amount=bid.amount,
                raw_message=message.text,
            )
        self._respond(store_id, message, client, outcome, bid.short_code, bid.amount)

    def _respond(
        self,
        store_id: UUID,
        message: IncomingMessage,
        client: ClientHandle,
        outcome: BidOutcome,
        short_code: str,
        amount: Decimal,
    ) -> None:
        reaction = react_to_outcome(outcome, short_code=short_code, amount=amount)
        if reaction.anomaly:
            self._log.warning(
                "resultado inesperado de place_bid",
                extra={"context": {"store_id": str(store_id), "outcome": outcome.outcome}},
            )
        self._act(store_id, message, client, reaction)

    def _act(
        self, store_id: UUID, message: IncomingMessage, client: ClientHandle, reaction: Reaction
    ) -> None:
        chat = message.chat
        if chat is None or reaction.action == "none":
            return
        if reaction.emoji and message.sender_jid:
            client.react(chat, message.sender_jid, message.message_id, reaction.emoji)
        if reaction.template_key and (reaction.action == "reply" or reaction.notify_ceiling):
            template = resolve_template(reaction.template_key, self._templates_for(store_id))
            client.send_text(chat, render(template, reaction.params))
