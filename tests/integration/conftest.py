"""Postgres real em contêiner efêmero, com as migrations do Backend e login REAL do bot_runtime.

O usuário padrão do contêiner é superusuário e ignora o RLS (ADR 0011): por isso o bot conecta
sempre como `bot_test`, membro do grupo `bot_runtime` (sem BYPASSRLS). O superusuário só semeia.

As migrations vêm do repositório irmão `../Backend/migrations` (ou de `BACKEND_MIGRATIONS_DIR`).
Sem elas, sem a migration `bot-runtime` ou sem Docker, os testes são PULADOS com o motivo.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

from pokemon_bot.db import Database

# O Ryuk (contêiner que apaga os outros) falha quando há vários testcontainers no mesmo Docker; a
# fixture já para o contêiner no `finally`.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

BOT_USER = "bot_test"
BOT_PASSWORD = "bot-test-password"


def _migrations_dir() -> Path:
    configured = os.environ.get("BACKEND_MIGRATIONS_DIR")
    return Path(configured) if configured else Path(__file__).parents[3] / "Backend" / "migrations"


@dataclass(frozen=True)
class Postgres:
    host: str
    port: int
    dbname: str
    admin_user: str
    admin_password: str

    def dsn(self, user: str, password: str) -> str:
        return f"postgresql://{user}:{password}@{self.host}:{self.port}/{self.dbname}"

    @property
    def admin_dsn(self) -> str:
        return self.dsn(self.admin_user, self.admin_password)

    @property
    def bot_dsn(self) -> str:
        return self.dsn(BOT_USER, BOT_PASSWORD)


@pytest.fixture(scope="session")
def postgres() -> Iterator[Postgres]:
    migrations = _migrations_dir()
    folders = sorted(p for p in migrations.glob("[0-9]*") if p.is_dir())
    if not folders or not any(p.name.endswith("bot-runtime") for p in folders):
        pytest.skip(f"migrations do Backend (com bot-runtime) não encontradas em {migrations}")

    try:
        from testcontainers.community.postgres import PostgresContainer

        container = PostgresContainer("postgres:17-alpine", dbname="app")
        container.start()
    except Exception as error:  # Docker ausente ou parado
        pytest.skip(f"Docker indisponível: {type(error).__name__}")

    try:
        pg = Postgres(
            host=container.get_container_host_ip(),
            port=int(container.get_exposed_port(5432)),
            dbname=container.dbname,
            admin_user=container.username,
            admin_password=container.password,
        )
        with psycopg.connect(pg.admin_dsn, autocommit=True) as admin:
            for folder in folders:
                admin.execute((folder / "up.sql").read_text(encoding="utf-8"))
            admin.execute(
                f"CREATE ROLE {BOT_USER} LOGIN PASSWORD '{BOT_PASSWORD}' IN ROLE bot_runtime"
            )
        yield pg
    finally:
        container.stop()  # remove o contêiner de teste


@pytest.fixture
def admin(postgres: Postgres) -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    with psycopg.connect(postgres.admin_dsn, autocommit=True) as conn:
        yield conn


@pytest.fixture
def db(postgres: Postgres) -> Iterator[Database]:
    database = Database(postgres.bot_dsn, min_size=1, max_size=4)
    yield database
    database.close()


@dataclass(frozen=True)
class Seed:
    """Uma loja com uma carta, um cliente e um leilão."""

    store_id: uuid.UUID
    card_id: uuid.UUID
    customer_id: uuid.UUID
    auction_id: uuid.UUID
    short_code: str


class Seeder:
    def __init__(self, admin: psycopg.Connection[tuple[object, ...]]) -> None:
        self.admin = admin
        self.catalog_id = f"cat-{uuid.uuid4().hex[:8]}"
        admin.execute(
            "INSERT INTO tcgdex_catalog (id, name, card_number, set_name, raw_data)"
            " VALUES (%s, 'Pikachu', '025/165', 'Base', %s::jsonb)",
            (self.catalog_id, '{"image": "https://assets.example/pikachu"}'),
        )

    def store(self, name: str = "Loja") -> uuid.UUID:
        row = self.admin.execute(
            "INSERT INTO stores (name) VALUES (%s) RETURNING id",
            (f"{name} {uuid.uuid4().hex[:6]}",),
        ).fetchone()
        assert row is not None
        return uuid.UUID(str(row[0]))

    def customer(
        self, store_id: uuid.UUID, phone: str | None = None, *, blacklisted: bool = False
    ) -> uuid.UUID:
        phone = phone or f"55119{uuid.uuid4().int % 10**8:08d}"
        row = self.admin.execute(
            "INSERT INTO customers (store_id, phone, name, is_blacklisted)"
            " VALUES (%s, %s, 'Cliente', %s) RETURNING id",
            (store_id, phone, blacklisted),
        ).fetchone()
        assert row is not None
        return uuid.UUID(str(row[0]))

    def card(self, store_id: uuid.UUID, short_code: str) -> uuid.UUID:
        row = self.admin.execute(
            "INSERT INTO cards_inventory (store_id, short_code, tcgdex_id, language, condition,"
            " ownership_type) VALUES (%s, %s, %s, 'PT', 'NM', 'OWN') RETURNING id",
            (store_id, short_code, self.catalog_id),
        ).fetchone()
        assert row is not None
        return uuid.UUID(str(row[0]))

    def auction(
        self,
        store_id: uuid.UUID,
        card_id: uuid.UUID,
        *,
        status: str = "ACTIVE",
        kind: str = "FREE_BID",
        start: datetime | None = None,
        end: datetime | None = None,
        initial: Decimal = Decimal("10"),
        increment: Decimal = Decimal("5"),
        ceiling: Decimal | None = None,
    ) -> uuid.UUID:
        now = datetime.now(timezone.utc)
        row = self.admin.execute(
            "INSERT INTO auctions (store_id, card_id, type, start_time, end_time, initial_bid,"
            " min_increment, max_poll_value, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " RETURNING id",
            (
                store_id,
                card_id,
                kind,
                start or now - timedelta(hours=1),
                end or now + timedelta(hours=1),
                initial,
                increment,
                ceiling,
                status,
            ),
        ).fetchone()
        assert row is not None
        return uuid.UUID(str(row[0]))

    def full(self, short_code: str | None = None, **auction_kwargs: object) -> Seed:
        code = short_code or f"S{uuid.uuid4().hex[:6].upper()}"
        store_id = self.store()
        card_id = self.card(store_id, code)
        auction_id = self.auction(store_id, card_id, **auction_kwargs)  # type: ignore[arg-type]
        return Seed(store_id, card_id, self.customer(store_id), auction_id, code)


@pytest.fixture
def seeder(admin: psycopg.Connection[tuple[object, ...]]) -> Seeder:
    return Seeder(admin)
