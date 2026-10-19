"""Ritmo humano no envio, para reduzir o risco de banimento (ADR 0007).

Cada envio espera um intervalo aleatório desde o anterior e respeita um teto por minuto. O relógio,
o sono e o sorteio são injetáveis: os testes não dormem de verdade.
"""

from __future__ import annotations

import random
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class PacingConfig:
    max_per_minute: int = 12
    min_gap: float = 1.5
    max_gap: float = 4.0

    def __post_init__(self) -> None:
        if self.max_per_minute < 1 or self.min_gap < 0 or self.max_gap < self.min_gap:
            raise ValueError("configuração de ritmo inválida")


# Mensagens e imagens são o que chama atenção; reações são mais leves.
MESSAGE_PACING = PacingConfig(max_per_minute=12, min_gap=1.5, max_gap=4.0)
REACTION_PACING = PacingConfig(max_per_minute=30, min_gap=0.4, max_gap=1.2)


class Pacer:
    """Bloqueia quem envia até a sua vez. Uma instância por loja e por tipo de envio."""

    def __init__(
        self,
        config: PacingConfig,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[float, float], float] = random.uniform,
    ) -> None:
        self._config = config
        self._clock = clock
        self._sleep = sleep
        self._jitter = jitter
        self._lock = threading.Lock()
        self._stamps: deque[float] = deque()
        self._last: float | None = None

    def wait_turn(self) -> float:
        """Espera o necessário e registra o envio. Devolve quantos segundos esperou."""
        with self._lock:
            now = self._clock()
            while self._stamps and now - self._stamps[0] >= 60:
                self._stamps.popleft()
            delay = 0.0
            if len(self._stamps) >= self._config.max_per_minute:
                delay = self._stamps[0] + 60 - now
            if self._last is not None:
                gap = self._jitter(self._config.min_gap, self._config.max_gap)
                delay = max(delay, self._last + gap - now)
            delay = max(delay, 0.0)
            if delay > 0:
                self._sleep(delay)
            sent_at = now + delay
            self._stamps.append(sent_at)
            self._last = sent_at
            return delay
