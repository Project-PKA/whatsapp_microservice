"""Uma sessão por loja. Só abre sozinha a loja que já tem sessão pareada; QR novo é pedido à parte.

Abrir QR para toda loja do banco geraria pedidos de pareamento que ninguém vai escanear. Quem
conecta uma loja nova chama `pair`. Como o painel pede isso ao bot ainda não está decidido
(OWNER.md, D20): hoje é uma chamada de código.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from uuid import UUID

from pokemon_bot import repository
from pokemon_bot.db import Database
from pokemon_bot.trigger.whatsapp.ports import ClientHandle
from pokemon_bot.trigger.whatsapp.session import StoreSession

SessionFactory = Callable[[UUID, bool], StoreSession]


class SessionManager:
    def __init__(
        self,
        db: Database,
        session_factory: SessionFactory,
        session_exists: Callable[[UUID], bool],
        logger: logging.Logger,
    ) -> None:
        self._db = db
        self._factory = session_factory
        self._exists = session_exists
        self._log = logger
        self._sessions: dict[UUID, StoreSession] = {}
        self._lock = threading.Lock()
        self.synced = False

    def sync(self) -> list[UUID]:
        """Abre as sessões pareadas que ainda não rodam. Devolve as abertas agora."""
        with self._db.platform_transaction() as conn:
            stores = repository.list_stores(conn)
        started: list[UUID] = []
        for store in stores:
            if self._exists(store.id) and self._start(store.id, new_device=False):
                started.append(store.id)
        self.synced = True
        return started

    def pair(self, store_id: UUID) -> bool:
        """Inicia o pareamento por QR de uma loja. `False` se já houver sessão rodando."""
        return self._start(store_id, new_device=True)

    def _start(self, store_id: UUID, *, new_device: bool) -> bool:
        with self._lock:
            current = self._sessions.get(store_id)
            if current is not None and current.running:
                return False
            session = self._factory(store_id, new_device)
            self._sessions[store_id] = session
        session.start()
        self._log.info(
            "sessão iniciada", extra={"context": {"store_id": str(store_id), "pair": new_device}}
        )
        return True

    def stop_all(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            session.stop()

    def online_clients(self) -> list[tuple[UUID, ClientHandle]]:
        """Sessões conectadas agora, com o cliente para enviar mensagens."""
        with self._lock:
            sessions = list(self._sessions.values())
        return [(s.store_id, s.handle) for s in sessions if s.online and s.handle is not None]

    def running_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.running)
