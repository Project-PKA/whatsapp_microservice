"""Servidor HTTP mínimo para liveness e readiness (docs/observability.md)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


def make_handler(is_ready: Callable[[], bool]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                self._reply(200, b"ok")
            elif self.path == "/ready":
                ready = is_ready()
                self._reply(200 if ready else 503, b"ready" if ready else b"not ready")
            else:
                self._reply(404, b"not found")

        def _reply(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            """Silencia o log padrão (não registra caminho nem cliente)."""

    return Handler


def start_health_server(
    port: int,
    is_ready: Callable[[], bool],
    host: str = "0.0.0.0",
) -> ThreadingHTTPServer:
    """Sobe o servidor numa thread daemon. Porta 0 escolhe uma livre (testes)."""
    server = ThreadingHTTPServer((host, port), make_handler(is_ready))
    threading.Thread(target=server.serve_forever, daemon=True, name="health").start()
    return server
