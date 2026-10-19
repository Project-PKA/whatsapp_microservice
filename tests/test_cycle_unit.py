from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from pokemon_bot.auction_cycle import format_deadline, photo_path
from pokemon_bot.bid_flow import GroupDirectory
from pokemon_bot.repository import AuctionRow

from .whatsapp.test_session_manager import FakeDb


def _auction(photos: list[object]) -> AuctionRow:
    now = datetime.now(timezone.utc)
    return AuctionRow(
        auction_id=uuid4(),
        card_id=uuid4(),
        short_code="A41",
        status="ACTIVE",
        auction_type="FREE_BID",
        start_time=now,
        end_time=now,
        initial_bid=Decimal("10"),
        min_increment=Decimal("5"),
        max_poll_value=None,
        card_name="Pikachu",
        card_number="25",
        set_name="Base",
        language="PT",
        condition="NM",
        is_foil=False,
        photos=photos,
        catalog_raw={},
    )


def test_prazo_em_horario_de_brasilia() -> None:
    assert format_deadline(datetime(2026, 10, 18, 23, 30, tzinfo=timezone.utc)) == "18/10 às 20:30"


def test_foto_sem_volume_ou_sem_arquivo() -> None:
    store = uuid4()
    assert photo_path(None, store, _auction(["a.webp"])) is None


def test_foto_ignora_caminhos_e_arquivos_inexistentes(tmp_path: Path) -> None:
    store, auction = uuid4(), _auction(["../x.webp", 5, "", "sub/y.webp", "ok.webp", "falta.webp"])
    folder = tmp_path / str(store) / str(auction.card_id)
    folder.mkdir(parents=True)
    (folder / "ok.webp").write_bytes(b"x")
    assert photo_path(tmp_path, store, auction) == folder / "ok.webp"
    assert photo_path(tmp_path, store, _auction([])) is None


def test_diretorio_de_grupos_usa_cache_e_recarrega() -> None:
    store = uuid4()
    db = FakeDb([store])
    clock = {"t": 0.0}
    groups = GroupDirectory(db, ttl=30, clock=lambda: clock["t"])  # type: ignore[arg-type]
    assert groups.group_of(store) is None
    assert groups.group_of(uuid4()) is None
    clock["t"] = 31
    assert groups.group_of(store) is None
