import json
import logging

from pokemon_bot.config import load_settings
from pokemon_bot.logging_setup import JsonFormatter


def test_settings_padrao_e_override() -> None:
    assert load_settings({}).health_port == 8080
    s = load_settings({"HEALTH_PORT": "9000", "LOG_LEVEL": "DEBUG", "ENVIRONMENT": "test"})
    assert (s.health_port, s.log_level, s.environment) == (9000, "debug", "test")


def test_log_json_nao_vaza_mensagem_da_excecao() -> None:
    try:
        raise ValueError("telefone 5511999999999")
    except ValueError:
        import sys

        rec = logging.LogRecord("x", logging.ERROR, "f", 1, "falhou", None, sys.exc_info())
    out = json.loads(JsonFormatter("svc").format(rec))
    assert out["exception"] == "ValueError"
    assert "5511" not in json.dumps(out)
    assert out["service"] == "svc" and out["level"] == "error"
