"""Conexão com o PostgreSQL do Backend, sempre com contexto de loja (ADR 0011).

Toda transação de negócio define `app.store_id` com `set_config(..., true)` (escopo LOCAL da
transação), nunca da sessão: uma conexão devolvida ao pool não carrega a loja anterior.
O papel de banco vem só da `DATABASE_URL` (provisório até o login do `bot_runtime` existir).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import psycopg
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool

Connection = psycopg.Connection[DictRow]


class Database:
    def __init__(self, dsn: str, *, min_size: int = 1, max_size: int = 5) -> None:
        self.dsn = dsn
        self._pool: ConnectionPool[Connection] = ConnectionPool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )

    @contextmanager
    def store_transaction(self, store_id: UUID) -> Iterator[Connection]:
        """Transação com `app.store_id` definido. Confirma ao sair; desfaz se houver exceção."""
        with self._pool.connection() as conn:
            conn.execute("SELECT set_config('app.store_id', %s, true)", (str(store_id),))
            yield conn

    @contextmanager
    def platform_transaction(self) -> Iterator[Connection]:
        """Transação SEM loja: só para o que o papel enxerga sem contexto (listar as lojas)."""
        with self._pool.connection() as conn:
            yield conn

    def close(self) -> None:
        self._pool.close()
