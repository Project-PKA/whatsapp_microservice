"""Ponto de entrada do worker. Por enquanto só sobe o health check."""

from __future__ import annotations

import signal
import threading

from pokemon_bot.config import load_settings
from pokemon_bot.logging_setup import configure_logging
from pokemon_bot.trigger.health import start_health_server


def main() -> None:
    settings = load_settings()
    log = configure_logging(settings.service_name, settings.log_level)
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    server = start_health_server(settings.health_port, is_ready=lambda: False)
    log.info("worker iniciado", extra={"context": {"health_port": settings.health_port}})
    stop.wait()
    server.shutdown()
    log.info("worker encerrado")


if __name__ == "__main__":
    main()
