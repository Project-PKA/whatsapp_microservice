"""Acesso às tabelas e funções do banco que o bot usa (docs/integration.md).

A REGRA DE LANCE NÃO ESTÁ AQUI: `place_bid` e `advance_auctions` são funções do PostgreSQL
(ADR 0016). Este módulo só chama, lê e converte. Cada função recebe a conexão de uma transação
que já definiu `app.store_id` (ver `db.Database.store_transaction`).

Nenhuma consulta devolve ou registra CPF, e-mail ou endereço: o papel do bot nem enxerga essas
colunas (migration 0021 do Backend).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pokemon_bot.db import Connection
from pokemon_bot.reactions import BidOutcome

OPEN_STATUSES = ("PENDING", "ACTIVE", "PAUSED_FOR_VALIDATION")


@dataclass(frozen=True)
class StoreRow:
    id: UUID
    name: str
    whatsapp_group_id: str | None
    whatsapp_status: str


@dataclass(frozen=True)
class CustomerRow:
    id: UUID
    phone: str
    name: str
    is_visitor: bool
    is_blacklisted: bool


@dataclass(frozen=True)
class AuctionRow:
    auction_id: UUID
    card_id: UUID
    short_code: str
    status: str
    auction_type: str
    start_time: datetime
    end_time: datetime
    initial_bid: Decimal
    min_increment: Decimal
    max_poll_value: Decimal | None
    card_name: str
    card_number: str
    set_name: str
    language: str
    condition: str
    is_foil: bool
    photos: list[Any]
    catalog_raw: dict[str, Any]


@dataclass(frozen=True)
class AdvanceResult:
    opened: int
    finished: int
    unsold: int


def list_stores(conn: Connection) -> list[StoreRow]:
    """Lojas que o bot enxerga sem contexto (id, nome, grupo e estado do WhatsApp)."""
    rows = conn.execute(
        "SELECT id, name, whatsapp_group_id, whatsapp_status::text AS whatsapp_status"
        " FROM stores ORDER BY name, id"
    ).fetchall()
    return [StoreRow(**row) for row in rows]


def set_whatsapp_status(
    conn: Connection, store_id: UUID, status: str, group_id: str | None = None
) -> bool:
    """Atualiza o estado do WhatsApp (e o grupo) pela função do Backend; `False` se recusou."""
    row = conn.execute(
        "SELECT bot_set_whatsapp_status(%s, %s::whatsapp_status, %s) AS ok",
        (store_id, status, group_id),
    ).fetchone()
    return bool(row and row["ok"])


def find_or_create_visitor(conn: Connection, store_id: UUID, phone: str, name: str) -> CustomerRow:
    """Cliente da loja pelo telefone; se não existe, cria o Visitante (ADR 0005).

    Concorrência-segura: dois primeiros lances do mesmo telefone ao mesmo tempo caem no
    `ON CONFLICT` e ambos leem a mesma linha. O nome de quem já existe nunca é alterado.
    """
    select = (
        "SELECT id, phone, name, is_visitor, is_blacklisted FROM customers"
        " WHERE store_id = %s AND phone = %s"
    )
    row = conn.execute(select, (store_id, phone)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO customers (store_id, phone, name) VALUES (%s, %s, %s)"
            " ON CONFLICT (store_id, phone) DO NOTHING",
            (store_id, phone, name),
        )
        row = conn.execute(select, (store_id, phone)).fetchone()
    if row is None:  # pragma: no cover - o INSERT ou o SELECT anterior garantem a linha
        raise RuntimeError("visitante não encontrado depois do INSERT")
    return CustomerRow(**row)


_AUCTION_SQL = """
SELECT a.id AS auction_id, a.card_id, c.short_code, a.status::text AS status,
       a.type::text AS auction_type, a.start_time, a.end_time, a.initial_bid, a.min_increment,
       a.max_poll_value, t.name AS card_name, t.card_number, t.set_name, c.language,
       c.condition::text AS condition, c.is_foil, c.custom_photos AS photos,
       t.raw_data AS catalog_raw
  FROM cards_inventory c
  JOIN auctions a ON a.card_id = c.id AND a.store_id = c.store_id
  JOIN tcgdex_catalog t ON t.id = c.tcgdex_id
 WHERE c.store_id = %(store)s AND {match}
 ORDER BY (a.status::text = ANY(%(open)s)) DESC, a.created_at DESC
 LIMIT 1
"""


def find_auction_by_short_code(
    conn: Connection, store_id: UUID, short_code: str
) -> AuctionRow | None:
    """Leilão da carta com esse `short_code`: o em andamento ou, se não houver, o mais recente.

    O mais recente (já encerrado ou cancelado) volta para `place_bid` responder
    `AUCTION_NOT_ACTIVE`, em vez de o bot ficar mudo. A caixa: a restrição do banco aceita `A41`
    e `a41` como cartas diferentes; tenta a correspondência exata e só depois a sem diferenciar
    caixa, e apenas quando ela é única (ambiguidade devolve `None`).
    """
    params = {"store": store_id, "open": list(OPEN_STATUSES), "code": short_code}
    row = conn.execute(_AUCTION_SQL.format(match="c.short_code = %(code)s"), params).fetchone()
    if row is None:
        cards = conn.execute(
            "SELECT count(*) AS n FROM cards_inventory"
            " WHERE store_id = %s AND upper(short_code) = upper(%s)",
            (store_id, short_code),
        ).fetchone()
        if cards is None or cards["n"] != 1:
            return None
        row = conn.execute(
            _AUCTION_SQL.format(match="upper(c.short_code) = upper(%(code)s)"), params
        ).fetchone()
    return AuctionRow(**row) if row else None


def place_bid(
    conn: Connection,
    *,
    store_id: UUID,
    auction_id: UUID,
    customer_id: UUID,
    amount: Decimal,
    raw_message: str,
    now: datetime | None = None,
) -> BidOutcome:
    """Chama `place_bid` do banco e devolve o resultado tipado. Não decide nada."""
    row = conn.execute(
        "SELECT outcome, min_amount, current_amount, new_status::text AS new_status,"
        " ceiling_reached FROM place_bid(%s, %s, %s, %s, %s, %s::timestamptz)",
        (store_id, auction_id, customer_id, amount, raw_message, now),
    ).fetchone()
    if row is None:  # pragma: no cover - a função sempre devolve uma linha
        raise RuntimeError("place_bid não devolveu resultado")
    return BidOutcome(
        outcome=row["outcome"],
        min_amount=row["min_amount"],
        current_amount=row["current_amount"],
        ceiling_reached=bool(row["ceiling_reached"]),
    )


def advance_auctions(
    conn: Connection, store_id: UUID, now: datetime | None = None
) -> AdvanceResult:
    """Abre, encerra e define vencedores pelo relógio (idempotente)."""
    row = conn.execute(
        "SELECT opened, finished, unsold"
        " FROM advance_auctions(%s, coalesce(%s::timestamptz, now()))",
        (store_id, now),
    ).fetchone()
    if row is None:  # pragma: no cover
        raise RuntimeError("advance_auctions não devolveu resultado")
    return AdvanceResult(row["opened"], row["finished"], row["unsold"])
