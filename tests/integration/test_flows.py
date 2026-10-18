"""Fluxos completos contra Postgres real: lance no grupo e ciclo do leilão (abrir e encerrar)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
import pytest

from pokemon_bot.auction_cycle import AuctionCycle, InMemoryLedger
from pokemon_bot.bid_flow import BidProcessor, GroupDirectory
from pokemon_bot.db import Database
from pokemon_bot.events import IncomingMessage
from pokemon_bot.moderation import Moderator
from pokemon_bot.participant import Address
from pokemon_bot.trigger.whatsapp.ports import GroupMember

from .conftest import Seed, Seeder

pytestmark = pytest.mark.integration

LOG = logging.getLogger("t.flows")
NOW = datetime.now(timezone.utc)
GROUP = "120363012345678901@g.us"
PHONE = "5511987654321"


class FakeClient:
    def __init__(self, lids: dict[str, str] | None = None) -> None:
        self.lids = lids or {}
        self.reactions: list[tuple[str, str, str, str]] = []
        self.texts: list[tuple[str, str]] = []
        self.images: list[tuple[str, str, str]] = []
        self.fail_sends = False
        self.members: list[GroupMember] = []
        self.removed: list[tuple[str, str]] = []
        self.fail_removals = False

    def run(self, events: Any) -> None: ...
    def stop(self) -> None: ...

    def send_text(self, chat: str, text: str) -> None:
        if self.fail_sends:
            raise RuntimeError("falha de rede")
        self.texts.append((chat, text))

    def send_image(self, chat: str, path: str, caption: str) -> None:
        if self.fail_sends:
            raise RuntimeError("falha de rede")
        self.images.append((chat, path, caption))

    def react(self, chat: str, sender: str, message_id: str, emoji: str) -> None:
        self.reactions.append((chat, sender, message_id, emoji))

    def group_participants(self, chat: str) -> list[GroupMember]:
        return self.members

    def remove_participant(self, chat: str, jid: str) -> None:
        if self.fail_removals:
            raise RuntimeError("not-authorized")
        self.removed.append((chat, jid))

    def resolve_lid(self, lid: Address) -> Address | None:
        phone = self.lids.get(lid.user)
        return Address(phone, "s.whatsapp.net") if phone else None


def _message(
    text: str,
    *,
    chat: str = GROUP,
    sender: Address | None = None,
    alt: Address | None = None,
    edit: bool = False,
    message_id: str = "MSG1",
) -> IncomingMessage:
    who = sender or Address(PHONE, "s.whatsapp.net")
    return IncomingMessage(
        message_id=message_id,
        is_group=True,
        is_from_me=False,
        is_edit=edit,
        text=text,
        sender=who,
        sender_alt=alt,
        display_name="Ash",
        chat=chat,
        sender_jid=f"{who.user}@{who.server}",
    )


@pytest.fixture
def processor(db: Database) -> BidProcessor:
    return BidProcessor(db, GroupDirectory(db, ttl=0), LOG)


def _with_group(admin: psycopg.Connection[tuple[object, ...]], seed: Seed) -> Seed:
    admin.execute("UPDATE stores SET whatsapp_group_id = %s WHERE id = %s", (GROUP, seed.store_id))
    return seed


def _bids(admin: psycopg.Connection[tuple[object, ...]], seed: Seed) -> list[tuple[Any, ...]]:
    return admin.execute(
        "SELECT b.amount, b.raw_whatsapp_message, c.phone, c.is_visitor FROM bids b"
        " JOIN customers c ON c.id = b.customer_id WHERE b.auction_id = %s ORDER BY b.amount",
        (seed.auction_id,),
    ).fetchall()


def test_lance_aceito_cria_visitante_registra_e_reage(
    processor: BidProcessor, seeder: Seeder, admin: psycopg.Connection[tuple[object, ...]]
) -> None:
    seed = _with_group(admin, seeder.full())
    client = FakeClient()
    processor.handle(seed.store_id, _message(f"#{seed.short_code} R$ 12,00"), client)
    assert _bids(admin, seed) == [(Decimal("12.00"), f"#{seed.short_code} R$ 12,00", PHONE, True)]
    assert client.reactions == [(GROUP, f"{PHONE}@s.whatsapp.net", "MSG1", "✅")]
    assert client.texts == []


def test_lance_baixo_responde_com_o_minimo(
    processor: BidProcessor, seeder: Seeder, admin: psycopg.Connection[tuple[object, ...]]
) -> None:
    seed = _with_group(admin, seeder.full())
    client = FakeClient()
    processor.handle(seed.store_id, _message(f"#{seed.short_code} 5"), client)
    assert client.reactions == [] and _bids(admin, seed) == []
    assert len(client.texts) == 1 and "R$ 10,00" in client.texts[0][1]


def test_enquete_no_teto_reage_e_avisa(
    processor: BidProcessor, seeder: Seeder, admin: psycopg.Connection[tuple[object, ...]]
) -> None:
    seed = _with_group(admin, seeder.full(kind="POLL", ceiling=Decimal("100")))
    client = FakeClient()
    processor.handle(seed.store_id, _message(f"#{seed.short_code} 100"), client)
    assert len(client.reactions) == 1
    assert len(client.texts) == 1 and "R$ 100,00" in client.texts[0][1]


@pytest.mark.parametrize(
    "case",
    ["outro_grupo", "editada", "sem_lance", "codigo_inexistente", "blacklist"],
)
def test_mensagens_ignoradas_ou_em_silencio(
    case: str,
    processor: BidProcessor,
    seeder: Seeder,
    admin: psycopg.Connection[tuple[object, ...]],
) -> None:
    seed = _with_group(admin, seeder.full())
    client = FakeClient()
    text = f"#{seed.short_code} 50"
    if case == "outro_grupo":
        msg = _message(text, chat="999999999999999999@g.us")
    elif case == "editada":
        msg = _message(text, edit=True)
    elif case == "sem_lance":
        msg = _message("bom dia pessoal")
    elif case == "codigo_inexistente":
        msg = _message("#ZZZ999 50")
    else:
        seeder.customer(seed.store_id, PHONE, blacklisted=True)
        msg = _message(text)
    processor.handle(seed.store_id, msg, client)
    assert (client.reactions, client.texts) == ([], [])
    assert _bids(admin, seed) == []


def test_loja_sem_grupo_definido_ignora(
    processor: BidProcessor, seeder: Seeder, admin: psycopg.Connection[tuple[object, ...]]
) -> None:
    seed = seeder.full()  # sem whatsapp_group_id
    client = FakeClient()
    processor.handle(seed.store_id, _message(f"#{seed.short_code} 50"), client)
    assert client.reactions == [] and _bids(admin, seed) == []


def test_lid_resolvido_usa_o_telefone_e_nao_resolvido_nao_cria_cliente(
    processor: BidProcessor, seeder: Seeder, admin: psycopg.Connection[tuple[object, ...]]
) -> None:
    seed = _with_group(admin, seeder.full())
    lid = Address("219807853060204", "lid")
    resolved = FakeClient({"219807853060204": PHONE})
    processor.handle(seed.store_id, _message(f"#{seed.short_code} 20", sender=lid), resolved)
    assert [b[2] for b in _bids(admin, seed)] == [PHONE]
    assert resolved.reactions[0][1] == "219807853060204@lid"  # reage ao remetente original

    other = _with_group(admin, seeder.full())
    unresolved = FakeClient()
    processor.handle(other.store_id, _message(f"#{other.short_code} 20", sender=lid), unresolved)
    assert _bids(admin, other) == [] and unresolved.reactions == []
    count = admin.execute(
        "SELECT count(*) FROM customers WHERE store_id = %s", (other.store_id,)
    ).fetchone()
    assert count == (1,)  # só o cliente do seed; ninguém foi criado


def test_codigo_em_minusculas_acha_a_carta(
    processor: BidProcessor, seeder: Seeder, admin: psycopg.Connection[tuple[object, ...]]
) -> None:
    seed = _with_group(admin, seeder.full("Q7"))
    client = FakeClient()
    processor.handle(seed.store_id, _message("#q7 20"), client)
    assert len(_bids(admin, seed)) == 1


def test_erro_de_banco_sobe_para_o_handler_blindado(seeder: Seeder, db: Database) -> None:
    class Boom:
        def group_of(self, _store: uuid.UUID) -> str:
            raise RuntimeError("banco fora")

    proc = BidProcessor(db, Boom(), LOG)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError):
        proc.handle(uuid.uuid4(), _message("#A1 5"), FakeClient())


# --- ciclo do leilão -----------------------------------------------------------------------------


def _cycle(db: Database, **kwargs: Any) -> AuctionCycle:
    return AuctionCycle(db, LOG, ledger=InMemoryLedger(), **kwargs)


def test_abre_o_leilao_uma_vez_com_a_legenda(db: Database, seeder: Seeder) -> None:
    seed = seeder.full(
        status="PENDING", start=NOW - timedelta(minutes=1), end=NOW + timedelta(hours=2)
    )
    cycle, client = _cycle(db), FakeClient()
    cycle.tick(seed.store_id, GROUP, client, NOW)
    assert len(client.texts) == 1 and client.images == []
    chat, caption = client.texts[0]
    assert chat == GROUP and "Pikachu" in caption and f"#{seed.short_code}" in caption
    assert "R$ 10,00" in caption and "R$ 5,00" in caption
    cycle.tick(seed.store_id, GROUP, client, NOW + timedelta(seconds=30))
    assert len(client.texts) == 1  # não repete


def test_abertura_com_foto_do_volume(db: Database, seeder: Seeder, tmp_path: Path) -> None:
    seed = seeder.full(start=NOW - timedelta(minutes=1), end=NOW + timedelta(hours=2))
    folder = tmp_path / str(seed.store_id) / str(seed.card_id)
    folder.mkdir(parents=True)
    (folder / "abc.webp").write_bytes(b"img")
    seeder.admin.execute(
        "UPDATE cards_inventory SET custom_photos = %s::jsonb WHERE id = %s",
        ('["../escape.webp", "abc.webp"]', seed.card_id),
    )
    client = FakeClient()
    _cycle(db, storage_dir=tmp_path).tick(seed.store_id, GROUP, client, NOW)
    assert client.texts == []
    assert len(client.images) == 1 and client.images[0][1].endswith("abc.webp")


def test_falha_no_envio_nao_marca_como_anunciado(db: Database, seeder: Seeder) -> None:
    seed = seeder.full(start=NOW - timedelta(minutes=1), end=NOW + timedelta(hours=2))
    cycle, client = _cycle(db), FakeClient()
    client.fail_sends = True
    cycle.tick(seed.store_id, GROUP, client, NOW)
    assert client.texts == []
    client.fail_sends = False
    cycle.tick(seed.store_id, GROUP, client, NOW + timedelta(seconds=60))
    assert len(client.texts) == 1  # tentou de novo na passada seguinte


def test_encerra_e_marca_o_vencedor(
    db: Database,
    processor: BidProcessor,
    seeder: Seeder,
    admin: psycopg.Connection[tuple[object, ...]],
) -> None:
    seed = _with_group(
        admin, seeder.full(start=NOW - timedelta(minutes=1), end=NOW + timedelta(minutes=5))
    )
    cycle, client = _cycle(db), FakeClient()
    cycle.tick(seed.store_id, GROUP, client, NOW)  # anuncia a abertura
    processor.handle(seed.store_id, _message(f"#{seed.short_code} 10"), client)
    processor.handle(
        seed.store_id,
        _message(f"#{seed.short_code} 30", sender=Address("5521911112222", "s.whatsapp.net")),
        client,
    )
    client.texts.clear()
    cycle.tick(seed.store_id, GROUP, client, NOW + timedelta(hours=1))
    assert len(client.texts) == 1
    announced = client.texts[0][1]
    assert "@5521911112222" in announced and "R$ 30,00" in announced and "Pikachu" in announced
    cycle.tick(seed.store_id, GROUP, client, NOW + timedelta(hours=1, minutes=1))
    assert len(client.texts) == 1  # só uma vez


def test_encerra_sem_lances_anuncia_que_nao_vendeu(db: Database, seeder: Seeder) -> None:
    seed = seeder.full(start=NOW - timedelta(minutes=1), end=NOW + timedelta(minutes=5))
    cycle, client = _cycle(db), FakeClient()
    cycle.tick(seed.store_id, GROUP, client, NOW)
    client.texts.clear()
    cycle.tick(seed.store_id, GROUP, client, NOW + timedelta(hours=1))
    assert len(client.texts) == 1 and "sem lances" in client.texts[0][1]


def test_apos_reinicio_anuncia_o_que_encerrou_dentro_da_janela(
    db: Database, seeder: Seeder
) -> None:
    seed = seeder.full(
        status="FINISHED", start=NOW - timedelta(hours=2), end=NOW - timedelta(minutes=3)
    )
    client = FakeClient()
    _cycle(db).tick(seed.store_id, GROUP, client, NOW)
    assert len(client.texts) == 1 and "sem lances" in client.texts[0][1]
    old = seeder.full(status="FINISHED", start=NOW - timedelta(days=2), end=NOW - timedelta(days=1))
    old_client = FakeClient()
    _cycle(db).tick(old.store_id, GROUP, old_client, NOW)
    assert old_client.texts == []  # fora da janela: não anuncia


def test_leilao_cancelado_nao_e_anunciado(db: Database, seeder: Seeder) -> None:
    seed = seeder.full(status="CANCELLED", start=NOW - timedelta(minutes=1))
    client = FakeClient()
    _cycle(db).tick(seed.store_id, GROUP, client, NOW)
    assert client.texts == [] and client.images == []


# --- moderação -----------------------------------------------------------------------------------


def _member(phone: str | None, *, admin: bool = False) -> GroupMember:
    jid = f"{phone or '999'}@{'s.whatsapp.net' if phone else 'lid'}"
    return GroupMember(jid=jid, phone=phone, is_admin=admin)


def test_remove_so_quem_esta_na_blacklist(db: Database, seeder: Seeder) -> None:
    store = seeder.store()
    seeder.customer(store, "5511900000001", blacklisted=True)
    seeder.customer(store, "5511900000002", blacklisted=True)  # admin: nunca remove
    seeder.customer(store, "5511900000003")  # cliente comum
    client = FakeClient()
    client.members = [
        _member("5511900000001"),
        _member("5511900000002", admin=True),
        _member("5511900000003"),
        _member("5511900000004"),  # nem é cliente
        _member(None),  # só LID
    ]
    result = Moderator(db, LOG).sweep(store, GROUP, client)
    assert client.removed == [(GROUP, "5511900000001@s.whatsapp.net")]
    assert (result.removed, result.skipped_admin, result.unresolved, result.failed) == (1, 1, 1, 0)


def test_sem_blacklist_nem_consulta_o_grupo(db: Database, seeder: Seeder) -> None:
    store = seeder.store()
    seeder.customer(store)

    class Explodes(FakeClient):
        def group_participants(self, chat: str) -> list[GroupMember]:
            raise AssertionError("não devia consultar")

    assert Moderator(db, LOG).sweep(store, GROUP, Explodes()).removed == 0


def test_limite_por_passada_e_o_resto_fica_para_a_proxima(db: Database, seeder: Seeder) -> None:
    store = seeder.store()
    phones = [f"551190000010{i}" for i in range(5)]
    for phone in phones:
        seeder.customer(store, phone, blacklisted=True)
    client = FakeClient()
    client.members = [_member(p) for p in phones]
    moderator = Moderator(db, LOG, max_per_pass=2)
    first = moderator.sweep(store, GROUP, client)
    assert (first.removed, first.pending) == (2, 3)
    second = moderator.sweep(store, GROUP, client)
    assert second.removed == 2 and len(client.removed) == 4


def test_para_de_insistir_depois_das_tentativas(db: Database, seeder: Seeder) -> None:
    store = seeder.store()
    seeder.customer(store, "5511900000020", blacklisted=True)
    client = FakeClient()
    client.members = [_member("5511900000020")]
    client.fail_removals = True
    moderator = Moderator(db, LOG, max_attempts=2)
    assert moderator.sweep(store, GROUP, client).failed == 1
    assert moderator.sweep(store, GROUP, client).failed == 1
    assert moderator.sweep(store, GROUP, client).failed == 0  # desistiu
    client.fail_removals = False
    assert moderator.sweep(store, GROUP, client).removed == 0
