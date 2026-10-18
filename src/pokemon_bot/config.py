"""Configuração por variáveis de ambiente. Nenhum segredo vive no código."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    environment: str
    log_level: str
    health_port: int


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Lê as variáveis de ambiente (ou o mapa recebido, nos testes)."""
    e = os.environ if env is None else env
    return Settings(
        service_name=e.get("SERVICE_NAME", "whatsapp-microservice"),
        environment=e.get("ENVIRONMENT", "development"),
        log_level=e.get("LOG_LEVEL", "info").lower(),
        health_port=int(e.get("HEALTH_PORT", "8080")),
    )
