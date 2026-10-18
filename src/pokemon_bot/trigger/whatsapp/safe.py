"""Nenhuma exceção pode escapar para o callback do whatsmeow.

Se uma exceção atravessa o callback ctypes do whatsmeow, o erro sai como "Exception ignored on
calling ctypes callback function" e o cliente segue num estado confuso (lição do spike). Todo
handler registrado no neonize passa por `guarded`.

O log leva só o NOME do handler e o TIPO da exceção: a mensagem da exceção pode carregar telefone,
nome ou texto de lance.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def guarded(logger: logging.Logger, name: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as error:
                logger.error(
                    "falha no handler",
                    extra={"context": {"handler": name, "error": type(error).__name__}},
                )
                return None

        return wrapper  # type: ignore[return-value]

    return decorator
