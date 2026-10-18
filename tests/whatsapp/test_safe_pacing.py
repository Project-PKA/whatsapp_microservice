import json
import logging

import pytest

from pokemon_bot.logging_setup import JsonFormatter
from pokemon_bot.trigger.whatsapp.pacing import Pacer, PacingConfig
from pokemon_bot.trigger.whatsapp.safe import guarded


def test_guarded_engole_excecao_e_nao_loga_a_mensagem(caplog: pytest.LogCaptureFixture) -> None:
    log = logging.getLogger("t.safe")

    @guarded(log, "msg")
    def boom() -> None:
        raise ValueError("telefone 5511999990000 e texto #A41 50")

    with caplog.at_level(logging.ERROR, logger="t.safe"):
        assert boom() is None
    assert "5511" not in caplog.text and "#A41" not in caplog.text
    record = caplog.records[0]
    assert record.context == {"handler": "msg", "error": "ValueError"}  # type: ignore[attr-defined]
    assert json.loads(JsonFormatter("s").format(record))["context"]["error"] == "ValueError"


def test_guarded_mantem_o_retorno() -> None:
    @guarded(logging.getLogger("t.safe2"), "ok")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(1, b=2) == 3


def test_guarded_nao_engole_interrupcao() -> None:
    @guarded(logging.getLogger("t.safe3"), "kbd")
    def interrupt() -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        interrupt()


class FakeTime:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _pacer(t: FakeTime, config: PacingConfig) -> Pacer:
    return Pacer(config, clock=t.clock, sleep=t.sleep, jitter=lambda lo, _hi: lo)


def test_primeiro_envio_nao_espera() -> None:
    t = FakeTime()
    assert _pacer(t, PacingConfig(10, 2.0, 3.0)).wait_turn() == 0
    assert t.slept == []


def test_intervalo_minimo_entre_envios() -> None:
    t = FakeTime()
    p = _pacer(t, PacingConfig(10, 2.0, 3.0))
    p.wait_turn()
    t.now += 0.5
    assert p.wait_turn() == pytest.approx(1.5)


def test_sem_espera_se_o_intervalo_ja_passou() -> None:
    t = FakeTime()
    p = _pacer(t, PacingConfig(10, 2.0, 3.0))
    p.wait_turn()
    t.now += 10
    assert p.wait_turn() == 0


def test_teto_por_minuto() -> None:
    t = FakeTime()
    p = _pacer(t, PacingConfig(3, 0.0, 0.0))
    for _ in range(3):
        p.wait_turn()
    # O quarto precisa esperar o primeiro sair da janela de 60 s.
    assert p.wait_turn() == pytest.approx(60)


def test_janela_desliza() -> None:
    t = FakeTime()
    p = _pacer(t, PacingConfig(2, 0.0, 0.0))
    p.wait_turn()
    p.wait_turn()
    t.now += 61
    assert p.wait_turn() == 0


@pytest.mark.parametrize("args", [(0, 1.0, 2.0), (5, -1.0, 2.0), (5, 3.0, 2.0)])
def test_configuracao_invalida(args: tuple[int, float, float]) -> None:
    with pytest.raises(ValueError):
        PacingConfig(*args)
