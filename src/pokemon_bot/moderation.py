"""Moderação: tirar do grupo quem está na blacklist da loja (glossário, "Blacklist").

Regras de segurança:

- Nunca remove administrador do grupo.
- No máximo `max_per_pass` remoções por passada (a cada minuto): sem rajada, e o resto sai na
  seguinte. O ritmo entre remoções é do cliente (`MODERATION_PACING`).
- O bot NUNCA adiciona participante (maior gatilho de ban, ADR 0015).
- Participante só com LID (sem telefone) não casa com a blacklist: é contado, não removido.
- Cada telefone tem no máximo `max_attempts` tentativas (o WhatsApp recusa quando o bot não é
  administrador do grupo); depois disso o bot para de insistir e registra o fato uma vez.

O log leva só contagens e o id da loja, nunca telefone nem nome.
"""

from __future__ import annotations

import logging
import threading
from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from pokemon_bot import repository
from pokemon_bot.db import Database
from pokemon_bot.trigger.whatsapp.ports import ClientHandle


@dataclass(frozen=True)
class SweepResult:
    removed: int = 0
    failed: int = 0
    skipped_admin: int = 0
    unresolved: int = 0
    pending: int = 0


class Moderator:
    def __init__(
        self,
        db: Database,
        logger: logging.Logger,
        *,
        max_per_pass: int = 3,
        max_attempts: int = 3,
    ) -> None:
        self._db = db
        self._log = logger
        self._max_per_pass = max_per_pass
        self._max_attempts = max_attempts
        self._lock = threading.Lock()
        self._attempts: Counter[tuple[UUID, str]] = Counter()

    def _gave_up(self, key: tuple[UUID, str]) -> bool:
        with self._lock:
            return self._attempts[key] >= self._max_attempts

    def _remove(
        self, store_id: UUID, group_id: str, client: ClientHandle, key: tuple[UUID, str], jid: str
    ) -> bool:
        with self._lock:
            self._attempts[key] += 1
            last_attempt = self._attempts[key] >= self._max_attempts
        try:
            client.remove_participant(group_id, jid)
        except Exception as error:
            self._log.warning(
                "falha ao remover participante da blacklist",
                extra={
                    "context": {
                        "store_id": str(store_id),
                        "error": type(error).__name__,
                        "gave_up": last_attempt,
                    }
                },
            )
            return False
        return True

    def sweep(self, store_id: UUID, group_id: str, client: ClientHandle) -> SweepResult:
        with self._db.store_transaction(store_id) as conn:
            blacklisted = repository.list_blacklisted_phones(conn, store_id)
        if not blacklisted:
            return SweepResult()

        members = client.group_participants(group_id)
        removed = failed = skipped_admin = unresolved = pending = 0
        for member in members:
            if member.phone is None:
                unresolved += 1
                continue
            if member.phone not in blacklisted:
                continue
            if member.is_admin:
                skipped_admin += 1
                continue
            key = (store_id, member.phone)
            if self._gave_up(key):
                continue
            if removed + failed >= self._max_per_pass:
                pending += 1
                continue
            if self._remove(store_id, group_id, client, key, member.jid):
                removed += 1
            else:
                failed += 1
        result = SweepResult(removed, failed, skipped_admin, unresolved, pending)
        if removed or failed:
            self._log.info(
                "moderação",
                extra={"context": {"store_id": str(store_id), **result.__dict__}},
            )
        return result
