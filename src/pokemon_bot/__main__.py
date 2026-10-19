"""Ponto de entrada do worker.

Sem `DATABASE_URL` sobe só o health check. Com ela, abre as sessões de WhatsApp das lojas que já
têm sessão pareada e confere o banco a cada minuto por lojas novas.
"""

from __future__ import annotations

import logging
import signal
import threading
from pathlib import Path
from uuid import UUID

from pokemon_bot.auction_cycle import AuctionCycle
from pokemon_bot.bid_flow import BidProcessor, GroupDirectory
from pokemon_bot.config import Settings, load_settings
from pokemon_bot.db import Database
from pokemon_bot.logging_setup import configure_logging
from pokemon_bot.trigger.health import start_health_server
from pokemon_bot.trigger.whatsapp.manager import SessionManager
from pokemon_bot.trigger.whatsapp.neonize_handle import NeonizeHandle
from pokemon_bot.trigger.whatsapp.qr_console import ConsoleQrSink
from pokemon_bot.trigger.whatsapp.session import StoreSession
from pokemon_bot.trigger.whatsapp.status import DbStatusReporter

SYNC_INTERVAL_SECONDS = 60


def build_manager(
    settings: Settings, db: Database, groups: GroupDirectory, log: logging.Logger
) -> SessionManager:
    reporter = DbStatusReporter(db, log)
    processor = BidProcessor(db, groups, log)
    qr_sink = ConsoleQrSink() if settings.console_qr else None

    def session_path(store_id: UUID) -> str:
        return settings.session_db_template.format(store_id=store_id)

    def make_session(store_id: UUID, new_device: bool) -> StoreSession:
        path = session_path(store_id)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        return StoreSession(
            store_id,
            lambda: NeonizeHandle(path, store_id, new_device=new_device),
            reporter,
            log,
            qr_sink=qr_sink,
            on_message=processor.handle,
        )

    return SessionManager(db, make_session, lambda sid: Path(session_path(sid)).exists(), log)


def run_pass(
    manager: SessionManager, groups: GroupDirectory, cycle: AuctionCycle, log: logging.Logger
) -> None:
    """Uma passada por minuto: abre sessões novas e roda o ciclo do leilão de cada loja online."""
    try:
        manager.sync()
    except Exception as error:
        log.error("falha ao sincronizar lojas", extra={"context": {"error": type(error).__name__}})
    for store_id, client in manager.online_clients():
        try:
            group_id = groups.group_of(store_id)
            if group_id:
                cycle.tick(store_id, group_id, client)
        except Exception as error:
            log.error(
                "falha no ciclo do leilão",
                extra={"context": {"store_id": str(store_id), "error": type(error).__name__}},
            )


def main() -> None:
    settings = load_settings()
    log = configure_logging(settings.service_name, settings.log_level)
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())

    db: Database | None = None
    manager: SessionManager | None = None
    groups: GroupDirectory | None = None
    cycle: AuctionCycle | None = None
    if settings.database_url:
        db = Database(settings.database_url)
        groups = GroupDirectory(db)
        manager = build_manager(settings, db, groups, log)
        storage = Path(settings.storage_dir) if settings.storage_dir else None
        cycle = AuctionCycle(db, log, storage_dir=storage)

    server = start_health_server(
        settings.health_port, is_ready=lambda: manager is not None and manager.synced
    )
    log.info("worker iniciado", extra={"context": {"health_port": settings.health_port}})
    try:
        while not stop.is_set():
            if manager is not None and groups is not None and cycle is not None:
                run_pass(manager, groups, cycle, log)
            stop.wait(SYNC_INTERVAL_SECONDS)
    finally:
        if manager is not None:
            manager.stop_all()
        if db is not None:
            db.close()
        server.shutdown()
        log.info("worker encerrado")


if __name__ == "__main__":
    main()
