import io
import json
import logging

from pokemon_bot.logging_setup import configure_logging


def test_configure_logging_emite_json_com_contexto() -> None:
    logger = configure_logging("svc", "debug")
    stream = io.StringIO()
    logger.handlers[0].setStream(stream)  # type: ignore[attr-defined]
    logger.info("olá", extra={"context": {"store_id": "x"}})
    line = json.loads(stream.getvalue())
    assert (line["service"], line["level"], line["message"]) == ("svc", "info", "olá")
    assert line["context"] == {"store_id": "x"} and line["trace_id"] is None
    assert logger.level == logging.DEBUG and not logger.propagate


def test_configure_logging_nivel_invalido_cai_para_info_e_nao_duplica_handler() -> None:
    configure_logging("svc", "nada")
    logger = configure_logging("svc", "nada")
    assert logger.level == logging.INFO and len(logger.handlers) == 1


def test_log_de_excecao_leva_so_o_tipo() -> None:
    logger = configure_logging("svc", "info")
    stream = io.StringIO()
    logger.handlers[0].setStream(stream)  # type: ignore[attr-defined]
    try:
        raise KeyError("5511999990000")
    except KeyError:
        logger.exception("falhou")
    out = stream.getvalue()
    assert json.loads(out)["exception"] == "KeyError" and "5511" not in out
