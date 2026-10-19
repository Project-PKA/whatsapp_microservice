from __future__ import annotations

import logging

import pytest

from pokemon_bot import repository as repo
from pokemon_bot.db import Database
from pokemon_bot.trigger.whatsapp.status import DbStatusReporter

from .conftest import Seeder

pytestmark = pytest.mark.integration


def _status(db: Database, store_id: object) -> str:
    with db.platform_transaction() as conn:
        return next(s.whatsapp_status for s in repo.list_stores(conn) if s.id == store_id)


def test_reporter_grava_o_estado_e_so_quando_muda(db: Database, seeder: Seeder) -> None:
    store = seeder.store()
    reporter = DbStatusReporter(db, logging.getLogger("t.status"))
    reporter.report(store, "QR_READY")
    assert _status(db, store) == "QR_READY"
    reporter.report(store, "ONLINE")
    assert _status(db, store) == "ONLINE"
    # Mudança por fora (ex.: o painel) e o mesmo estado reportado de novo: não reescreve.
    with db.store_transaction(store) as conn:
        repo.set_whatsapp_status(conn, store, "OFFLINE")
    reporter.report(store, "ONLINE")
    assert _status(db, store) == "OFFLINE"
