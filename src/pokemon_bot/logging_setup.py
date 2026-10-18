"""Log estruturado em JSON, uma linha por evento (docs/observability.md).

Regra do projeto: nunca registrar telefone, nome, CPF, token nem texto de mensagem de lance.
Quem chama deve passar só identificadores internos e contagens em `context`.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "error": logging.ERROR,
}


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "service": self._service,
            "trace_id": getattr(record, "trace_id", None),
            "message": record.getMessage(),
            "context": getattr(record, "context", {}),
        }
        if record.exc_info:
            # Só o tipo da exceção: a mensagem pode carregar dado pessoal.
            payload["exception"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(service: str, level: str) -> logging.Logger:
    logger = logging.getLogger("pokemon_bot")
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service))
    logger.addHandler(handler)
    logger.setLevel(_LEVELS.get(level, logging.INFO))
    logger.propagate = False
    return logger
