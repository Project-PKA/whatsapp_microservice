"""Publica o estado da conexão no banco (`bot_set_whatsapp_status`), só quando muda."""

from __future__ import annotations

import logging
import threading
from uuid import UUID

from pokemon_bot import repository
from pokemon_bot.db import Database


class DbStatusReporter:
    def __init__(self, db: Database, logger: logging.Logger) -> None:
        self._db = db
        self._log = logger
        self._last: dict[UUID, str] = {}
        self._lock = threading.Lock()

    def report(self, store_id: UUID, status: str) -> None:
        with self._lock:
            if self._last.get(store_id) == status:
                return
        with self._db.store_transaction(store_id) as conn:
            ok = repository.set_whatsapp_status(conn, store_id, status)
        if not ok:
            self._log.warning(
                "banco recusou o estado do WhatsApp",
                extra={"context": {"store_id": str(store_id), "status": status}},
            )
            return
        with self._lock:
            self._last[store_id] = status
