"""Supervisor de UMA loja: mantém a conexão, reporta o estado e reconecta com espera crescente."""

from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Callable
from uuid import UUID

from pokemon_bot.events import IncomingMessage
from pokemon_bot.trigger.whatsapp.ports import ClientHandle, QrSink, StatusReporter
from pokemon_bot.trigger.whatsapp.safe import guarded

MessageHandler = Callable[[UUID, IncomingMessage, ClientHandle], None]


class Backoff:
    """Espera 2s, 4s, 8s... até o teto, com um pouco de variação. `reset` ao reconectar."""

    def __init__(
        self,
        *,
        base: float = 2.0,
        cap: float = 300.0,
        jitter: Callable[[float, float], float] = random.uniform,
    ) -> None:
        self._base = base
        self._cap = cap
        self._jitter = jitter
        self._attempt = 0

    def next(self) -> float:
        delay = min(self._cap, self._base * (2**self._attempt))
        self._attempt += 1
        return delay * self._jitter(0.8, 1.2) if delay < self._cap else self._cap

    def reset(self) -> None:
        self._attempt = 0


class StoreSession:
    def __init__(
        self,
        store_id: UUID,
        handle_factory: Callable[[], ClientHandle],
        reporter: StatusReporter,
        logger: logging.Logger,
        *,
        on_message: MessageHandler | None = None,
        qr_sink: QrSink | None = None,
        backoff: Backoff | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.store_id = store_id
        self._handle_factory = handle_factory
        self._reporter = reporter
        self._log = logger
        self._on_message = on_message
        self._qr_sink = qr_sink
        self._backoff = backoff or Backoff()
        self._sleep = sleep
        self._stop = threading.Event()
        self._logged_out = False
        self._handle: ClientHandle | None = None
        self._thread: threading.Thread | None = None
        # Cada callback é blindado: nenhuma exceção chega ao whatsmeow.
        self.on_qr = guarded(logger, "qr")(self._on_qr)
        self.on_connected = guarded(logger, "connected")(self._on_connected)
        self.on_disconnected = guarded(logger, "disconnected")(self._on_disconnected)
        self.on_logged_out = guarded(logger, "logged_out")(self._on_logged_out)
        self.on_message = guarded(logger, "message")(self._on_message_event)

    # --- ciclo de vida -------------------------------------------------------------------------
    def start(self) -> None:
        self._thread = threading.Thread(target=self.run, name=f"wa-{self.store_id}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        handle = self._handle
        if handle is not None:
            guarded(self._log, "stop")(handle.stop)()
        if self._thread is not None:
            self._thread.join(timeout=10)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def handle(self) -> ClientHandle | None:
        return self._handle

    def run(self) -> None:
        """Conecta, e se a conexão cair ou der erro, espera e tenta de novo. Termina no `stop`."""
        while not self._stop.is_set() and not self._logged_out:
            try:
                self._handle = self._handle_factory()
                self._handle.run(self)  # bloqueia até a conexão acabar
            except Exception as error:
                self._log.error(
                    "conexão encerrada com erro",
                    extra={
                        "context": {"store_id": str(self.store_id), "error": type(error).__name__}
                    },
                )
            if self._stop.is_set() or self._logged_out:
                break
            self._safe_report("OFFLINE")
            self._sleep(self._backoff.next())
        self._handle = None

    # --- eventos (sempre via os wrappers `on_*`) -------------------------------------------------
    def _safe_report(self, status: str) -> None:
        guarded(self._log, "report")(self._reporter.report)(self.store_id, status)

    def _on_qr(self, data: bytes) -> None:
        self._safe_report("QR_READY")
        if self._qr_sink is not None:
            self._qr_sink.publish(self.store_id, data)

    def _on_connected(self) -> None:
        self._backoff.reset()
        self._safe_report("ONLINE")

    def _on_disconnected(self) -> None:
        self._safe_report("OFFLINE")

    def _on_logged_out(self) -> None:
        # O WhatsApp desvinculou o aparelho: reconectar sozinho só geraria pedidos inválidos.
        self._logged_out = True
        self._safe_report("OFFLINE")

    def _on_message_event(self, message: IncomingMessage) -> None:
        handle = self._handle
        if self._on_message is not None and handle is not None:
            self._on_message(self.store_id, message, handle)
