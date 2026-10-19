"""Textos próprios de cada loja (`store_message_templates`), com cache curto.

O lance chama isto a cada resposta; por isso o banco só é consultado de novo depois do `ttl`. Se a
consulta falha, vale o último valor conhecido (ou nenhum, e então valem os padrões de
`templates.py`): um problema ao ler os textos nunca pode calar o bot.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Mapping
from uuid import UUID

from pokemon_bot import repository
from pokemon_bot.db import Database


class TemplateStore:
    def __init__(
        self,
        db: Database,
        logger: logging.Logger,
        *,
        ttl_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._db = db
        self._log = logger
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._cache: dict[UUID, tuple[float, dict[str, str]]] = {}

    def __call__(self, store_id: UUID) -> Mapping[str, str] | None:
        """Textos da loja (chave -> texto); vazio se ela usa só os padrões."""
        now = self._clock()
        with self._lock:
            cached = self._cache.get(store_id)
        if cached is not None and now - cached[0] < self._ttl:
            return cached[1]
        try:
            with self._db.store_transaction(store_id) as conn:
                fresh = repository.load_templates(conn, store_id)
        except Exception as error:
            self._log.error(
                "falha ao ler os modelos de mensagem",
                extra={"context": {"error": type(error).__name__}},
            )
            return cached[1] if cached is not None else None
        with self._lock:
            self._cache[store_id] = (now, fresh)
        return fresh
