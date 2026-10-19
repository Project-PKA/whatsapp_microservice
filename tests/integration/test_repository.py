"""Contra Postgres real, como o login do `bot_runtime`. Cada teste cria as próprias lojas."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import psycopg
import pytest

from pokemon_bot import repository as repo
from pokemon_bot.db import Database
from pokemon_bot.reactions import BidOutcome

from .conftest import BOT_USER, Seed, Seeder

pytestmark = pytest.mark.integration

NOW = datetime.now(timezone.utc)


def _bid(db: Database, seed: Seed, amount: str, *, now: datetime | None = None) -> BidOutcome:
    with db.store_transaction(seed.store_id) as conn:
        return repo.place_bid(
            conn,
            store_id=seed.store_id,
            auction_id=seed.auction_id,
            customer_id=seed.customer_id,
            amount=Decimal(amount),
            raw_message=f"#{seed.short_code} {amount}",
            now=now,
        )


def test_papel_do_bot_nao_e_superusuario_nem_ignora_rls(db: Database) -> None:
    with db.platform_transaction() as conn:
        row = conn.execute(
            "SELECT rolsuper, rolbypassrls, current_user AS who FROM pg_roles"
            " WHERE rolname = current_user"
        ).fetchone()
    assert row == {"rolsuper": False, "rolbypassrls": False, "who": BOT_USER}


def test_contexto_da_loja_nao_vaza_para_a_proxima_transacao(db: Database, seeder: Seeder) -> None:
    seed = seeder.full()
    pool_of_one = Database(db.dsn, min_size=1, max_size=1)
    try:
        with pool_of_one.store_transaction(seed.store_id) as conn:
            assert conn.execute("SELECT count(*) AS n FROM customers").fetchone() == {"n": 1}
        # Mesma conexão do pool, sem contexto: não enxerga nada.
        with pool_of_one.platform_transaction() as conn:
            assert conn.execute("SELECT count(*) AS n FROM customers").fetchone() == {"n": 0}
    finally:
        pool_of_one.close()


def test_loja_nao_enxerga_dados_de_outra(db: Database, seeder: Seeder) -> None:
    a, b = seeder.full(), seeder.full()
    with db.store_transaction(a.store_id) as conn:
        phones = conn.execute("SELECT phone FROM customers").fetchall()
        assert len(phones) == 1
        assert repo.find_auction_by_short_code(conn, a.store_id, b.short_code) is None
        # place_bid de outra loja não acha o leilão.
        outcome = repo.place_bid(
            conn,
            store_id=a.store_id,
            auction_id=b.auction_id,
            customer_id=a.customer_id,
            amount=Decimal("50"),
            raw_message="x",
        )
    assert outcome.outcome == "AUCTION_NOT_FOUND"


def test_lista_lojas_sem_contexto(db: Database, seeder: Seeder) -> None:
    a, b = seeder.store("Alfa"), seeder.store("Beta")
    with db.platform_transaction() as conn:
        ids = {s.id for s in repo.list_stores(conn)}
    assert {a, b} <= ids


def test_estado_do_whatsapp(db: Database, seeder: Seeder) -> None:
    store = seeder.store()
    other = seeder.store()
    with db.store_transaction(store) as conn:
        assert repo.set_whatsapp_status(conn, store, "ONLINE", "120363012345678901@g.us")
        assert not repo.set_whatsapp_status(conn, store, "OFFLINE", "grupo-invalido")
        assert not repo.set_whatsapp_status(conn, other, "ONLINE")  # outra loja
        assert repo.set_whatsapp_status(conn, store, "OFFLINE")  # mantém o grupo
    with db.platform_transaction() as conn:
        row = next(s for s in repo.list_stores(conn) if s.id == store)
        untouched = next(s for s in repo.list_stores(conn) if s.id == other)
    assert (row.whatsapp_status, row.whatsapp_group_id) == ("OFFLINE", "120363012345678901@g.us")
    assert untouched.whatsapp_status == "OFFLINE" and untouched.whatsapp_group_id is None


def test_visitante_criado_uma_vez_e_nome_preservado(db: Database, seeder: Seeder) -> None:
    store = seeder.store()
    with db.store_transaction(store) as conn:
        first = repo.find_or_create_visitor(conn, store, "5511999990001", "Ash")
        again = repo.find_or_create_visitor(conn, store, "5511999990001", "Outro Nome")
    assert first.id == again.id and again.name == "Ash"
    assert first.is_visitor and not first.is_blacklisted


def test_visitante_concorrente_nao_duplica(db: Database, seeder: Seeder) -> None:
    store = seeder.store()

    def create(_: int) -> uuid.UUID:
        with db.store_transaction(store) as conn:
            return repo.find_or_create_visitor(conn, store, "5511999990002", "Misty").id

    with ThreadPoolExecutor(4) as pool:
        ids = set(pool.map(create, range(8)))
    assert len(ids) == 1


def test_visitante_so_na_propria_loja(db: Database, seeder: Seeder) -> None:
    a, b = seeder.store(), seeder.store()
    with db.store_transaction(a) as conn:
        in_a = repo.find_or_create_visitor(conn, a, "5511999990003", "Brock")
    with db.store_transaction(b) as conn:
        in_b = repo.find_or_create_visitor(conn, b, "5511999990003", "Brock")
    assert in_a.id != in_b.id


def test_bot_nao_cria_visitante_em_outra_loja(db: Database, seeder: Seeder) -> None:
    a, b = seeder.store(), seeder.store()
    with pytest.raises(psycopg.errors.InsufficientPrivilege), db.store_transaction(a) as conn:
        conn.execute("INSERT INTO customers (store_id, phone, name) VALUES (%s, '1', 'x')", (b,))


def test_bot_nao_le_colunas_sensiveis(db: Database) -> None:
    with pytest.raises(psycopg.errors.InsufficientPrivilege), db.platform_transaction() as conn:
        conn.execute("SELECT cpf FROM customers")


def test_busca_por_short_code_exato_e_sem_caixa(db: Database, seeder: Seeder) -> None:
    store = seeder.store()
    card = seeder.card(store, "A41")
    seeder.auction(store, card)
    with db.store_transaction(store) as conn:
        exact = repo.find_auction_by_short_code(conn, store, "A41")
        lower = repo.find_auction_by_short_code(conn, store, "a41")
        missing = repo.find_auction_by_short_code(conn, store, "ZZ9")
    assert exact is not None and lower is not None and missing is None
    assert exact.auction_id == lower.auction_id
    assert (exact.card_name, exact.set_name, exact.status) == ("Pikachu", "Base", "ACTIVE")
    assert exact.catalog_raw["image"].startswith("https://")


def test_busca_nao_diferencia_caixa_porque_o_banco_guarda_em_maiusculas(
    db: Database, seeder: Seeder
) -> None:
    store = seeder.store()
    seeder.auction(store, seeder.card(store, "AB1"))
    with db.store_transaction(store) as conn:
        assert repo.find_auction_by_short_code(conn, store, "ab1") is not None
        assert repo.find_auction_by_short_code(conn, store, "Ab1") is not None
        assert repo.find_auction_by_short_code(conn, store, "AB2") is None


def test_busca_prefere_o_leilao_em_andamento_ao_encerrado(db: Database, seeder: Seeder) -> None:
    store = seeder.store()
    card = seeder.card(store, "R1")
    seeder.auction(
        store, card, status="FINISHED", end=NOW - timedelta(days=1), start=NOW - timedelta(days=2)
    )
    open_one = seeder.auction(store, card, status="ACTIVE")
    with db.store_transaction(store) as conn:
        found = repo.find_auction_by_short_code(conn, store, "R1")
    assert found is not None and found.auction_id == open_one


def test_busca_devolve_o_encerrado_quando_nao_ha_aberto(db: Database, seeder: Seeder) -> None:
    store = seeder.store()
    seeder.auction(
        store,
        seeder.card(store, "F1"),
        status="FINISHED",
        start=NOW - timedelta(days=2),
        end=NOW - timedelta(days=1),
    )
    with db.store_transaction(store) as conn:
        found = repo.find_auction_by_short_code(conn, store, "F1")
    assert found is not None and found.status == "FINISHED"


def test_place_bid_aceito_e_lance_baixo(db: Database, seeder: Seeder) -> None:
    seed = seeder.full()
    ok = _bid(db, seed, "10")
    assert ok.outcome == "ACCEPTED" and not ok.ceiling_reached
    low = _bid(db, seed, "12")
    assert low.outcome == "BID_TOO_LOW" and low.min_amount == Decimal("15")
    assert _bid(db, seed, "15").outcome == "ACCEPTED"


@pytest.mark.parametrize("amount", ["0", "50.555"])
def test_place_bid_valor_invalido(db: Database, seeder: Seeder, amount: str) -> None:
    assert _bid(db, seeder.full(), amount).outcome == "INVALID_AMOUNT"


def test_place_bid_cliente_na_blacklist(db: Database, seeder: Seeder) -> None:
    seed = seeder.full()
    black = seeder.customer(seed.store_id, blacklisted=True)
    with db.store_transaction(seed.store_id) as conn:
        result = repo.place_bid(
            conn,
            store_id=seed.store_id,
            auction_id=seed.auction_id,
            customer_id=black,
            amount=Decimal("50"),
            raw_message="x",
        )
    assert result.outcome == "CUSTOMER_BLACKLISTED"


def test_place_bid_antes_do_inicio_e_depois_do_fim(db: Database, seeder: Seeder) -> None:
    future = seeder.full(
        status="PENDING", start=NOW + timedelta(hours=1), end=NOW + timedelta(hours=2)
    )
    assert _bid(db, future, "20").outcome == "NOT_STARTED"
    past = seeder.full(start=NOW - timedelta(hours=2), end=NOW - timedelta(hours=1))
    assert _bid(db, past, "20").outcome == "ENDED"


def test_place_bid_leilao_nao_ativo(db: Database, seeder: Seeder) -> None:
    assert _bid(db, seeder.full(status="CANCELLED"), "20").outcome == "AUCTION_NOT_ACTIVE"


def test_enquete_no_teto_pausa_sem_encerrar(db: Database, seeder: Seeder) -> None:
    seed = seeder.full(kind="POLL", ceiling=Decimal("100"))
    result = _bid(db, seed, "100")
    assert result.outcome == "ACCEPTED" and result.ceiling_reached
    # Já pausado: o próximo lance não entra.
    assert _bid(db, seed, "200").outcome == "AUCTION_NOT_ACTIVE"


def test_lances_simultaneos_um_por_vez(db: Database, seeder: Seeder) -> None:
    seed = seeder.full()
    amounts = [str(10 + 5 * i) for i in range(8)]

    def go(amount: str) -> str:
        return _bid(db, seed, amount).outcome

    with ThreadPoolExecutor(4) as pool:
        outcomes = list(pool.map(go, amounts))
    assert set(outcomes) <= {"ACCEPTED", "BID_TOO_LOW"}
    assert "ACCEPTED" in outcomes
    with db.store_transaction(seed.store_id) as conn:
        top = conn.execute(
            "SELECT max(amount) AS top, count(*) AS n FROM bids WHERE auction_id = %s",
            (seed.auction_id,),
        ).fetchone()
    assert top is not None and top["top"] == Decimal("45")  # o maior sempre entra
    assert top["n"] == outcomes.count("ACCEPTED")


def test_advance_auctions_encerra_define_vencedor_e_e_idempotente(
    db: Database, seeder: Seeder, admin: psycopg.Connection[tuple[object, ...]]
) -> None:
    seed = seeder.full(end=NOW + timedelta(minutes=5))
    assert _bid(db, seed, "10").outcome == "ACCEPTED"
    top = _bid(db, seed, "20")
    assert top.outcome == "ACCEPTED"
    later = NOW + timedelta(hours=1)
    with db.store_transaction(seed.store_id) as conn:
        first = repo.advance_auctions(conn, seed.store_id, later)
    with db.store_transaction(seed.store_id) as conn:
        second = repo.advance_auctions(conn, seed.store_id, later)
    assert (first.finished, first.unsold) == (1, 0)
    assert (second.opened, second.finished) == (0, 0)
    row = admin.execute(
        "SELECT a.status::text, b.amount, c.status::text FROM auctions a"
        " JOIN bids b ON b.id = a.winning_bid_id JOIN cards_inventory c ON c.id = a.card_id"
        " WHERE a.id = %s",
        (seed.auction_id,),
    ).fetchone()
    assert row == ("FINISHED", Decimal("20.00"), "AWAITING_CONFIRMATION")


def test_advance_auctions_sem_lances_devolve_a_carta(
    db: Database, seeder: Seeder, admin: psycopg.Connection[tuple[object, ...]]
) -> None:
    seed = seeder.full(end=NOW + timedelta(minutes=5))
    with db.store_transaction(seed.store_id) as conn:
        result = repo.advance_auctions(conn, seed.store_id, NOW + timedelta(hours=1))
    assert (result.finished, result.unsold) == (1, 1)
    row = admin.execute(
        "SELECT status::text FROM cards_inventory WHERE id = %s", (seed.card_id,)
    ).fetchone()
    assert row == ("AVAILABLE",)


def test_advance_auctions_abre_leilao_pendente(db: Database, seeder: Seeder) -> None:
    seed = seeder.full(
        status="PENDING", start=NOW - timedelta(minutes=1), end=NOW + timedelta(hours=1)
    )
    with db.store_transaction(seed.store_id) as conn:
        assert repo.advance_auctions(conn, seed.store_id).opened == 1
