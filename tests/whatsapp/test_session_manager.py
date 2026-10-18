from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from pokemon_bot.events import IncomingMessage
from pokemon_bot.participant import Address
from pokemon_bot.trigger.whatsapp.manager import SessionManager
from pokemon_bot.trigger.whatsapp.ports import SessionEvents
from pokemon_bot.trigger.whatsapp.session import Backoff, StoreSession

LOG = logging.getLogger("t.session")


class Reporter:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, str]] = []

    def report(self, store_id: UUID, status: str) -> None:
        self.calls.append((store_id, status))

    def statuses(self) -> list[str]:
        return [s for _, s in self.calls]


class Sink:
    def __init__(self) -> None:
        self.published: list[tuple[UUID, bytes]] = []

    def publish(self, store_id: UUID, data: bytes) -> None:
        self.published.append((store_id, data))


class ScriptedHandle:
    """Cada `run` executa o próximo roteiro: uma função que recebe os eventos."""

    def __init__(self, scripts: list[Any]) -> None:
        self.scripts = scripts
        self.runs = 0
        self.stopped = False

    def run(self, events: SessionEvents) -> None:
        script = self.scripts[min(self.runs, len(self.scripts) - 1)]
        self.runs += 1
        script(events)

    def stop(self) -> None:
        self.stopped = True

    def send_text(self, chat: str, text: str) -> None: ...
    def send_image(self, chat: str, path: str, caption: str) -> None: ...
    def react(self, chat: str, sender: str, message_id: str, emoji: str) -> None: ...
    def resolve_lid(self, lid: Address) -> Address | None:
        return None


def _session(
    scripts: list[Any],
    reporter: Reporter,
    *,
    sleeps: list[float] | None = None,
    **kwargs: Any,
) -> tuple[StoreSession, ScriptedHandle]:
    handle = ScriptedHandle(scripts)
    sleeps = sleeps if sleeps is not None else []
    session = StoreSession(
        uuid4(),
        lambda: handle,
        reporter,
        LOG,
        backoff=Backoff(jitter=lambda lo, _hi: 1.0),
        sleep=sleeps.append,
        **kwargs,
    )
    return session, handle


def test_qr_conectado_e_desconectado_viram_estado() -> None:
    reporter, sink = Reporter(), Sink()

    def script(events: SessionEvents) -> None:
        events.on_qr(b"qr-data")
        events.on_connected()
        events.on_disconnected()
        session._stop.set()

    session, _ = _session([script], reporter, qr_sink=sink)
    session.run()
    assert reporter.statuses() == ["QR_READY", "ONLINE", "OFFLINE"]
    assert sink.published == [(session.store_id, b"qr-data")]


def test_reconecta_com_espera_crescente_e_zera_ao_conectar() -> None:
    reporter = Reporter()
    sleeps: list[float] = []
    state = {"n": 0}

    def script(events: SessionEvents) -> None:
        state["n"] += 1
        if state["n"] == 3:
            events.on_connected()  # zera a espera
        if state["n"] == 5:
            session._stop.set()
        raise ConnectionError("rede com dado 5511999990000")

    session, handle = _session([script], reporter, sleeps=sleeps)
    session.run()
    assert handle.runs == 5
    assert sleeps == [2.0, 4.0, 2.0, 4.0]  # depois do ONLINE recomeça em 2 s
    assert reporter.statuses().count("OFFLINE") == 4


def test_conexao_que_retorna_sem_erro_tambem_reconecta() -> None:
    reporter = Reporter()
    sleeps: list[float] = []
    calls = {"n": 0}

    def script(_events: SessionEvents) -> None:
        calls["n"] += 1
        if calls["n"] == 2:
            session._stop.set()

    session, handle = _session([script], reporter, sleeps=sleeps)
    session.run()
    assert handle.runs == 2 and sleeps == [2.0]


def test_logout_nao_reconecta() -> None:
    reporter = Reporter()

    def script(events: SessionEvents) -> None:
        events.on_logged_out()

    session, handle = _session([script], reporter)
    session.run()
    assert handle.runs == 1
    assert reporter.statuses() == ["OFFLINE"]


def test_erro_no_reporter_nao_derruba_a_sessao() -> None:
    class Broken(Reporter):
        def report(self, store_id: UUID, status: str) -> None:
            raise RuntimeError("banco fora")

    def script(events: SessionEvents) -> None:
        events.on_connected()
        events.on_qr(b"x")
        session._stop.set()

    session, handle = _session([script], Broken())
    session.run()
    assert handle.runs == 1


def test_mensagem_vai_ao_handler_e_erro_do_handler_nao_escapa() -> None:
    reporter = Reporter()
    seen: list[IncomingMessage] = []
    msg = IncomingMessage("m1", True, False, False, "#A41 50")

    def on_message(_store: UUID, message: IncomingMessage, _handle: Any) -> None:
        seen.append(message)
        raise RuntimeError("falha de negócio")

    def script(events: SessionEvents) -> None:
        events.on_message(msg)  # não pode lançar
        session._stop.set()

    session, _ = _session([script], reporter, on_message=on_message)
    session.run()
    assert seen == [msg]


def test_backoff_respeita_o_teto() -> None:
    b = Backoff(base=2.0, cap=10.0, jitter=lambda lo, _hi: 1.0)
    assert [b.next() for _ in range(5)] == [2.0, 4.0, 8.0, 10.0, 10.0]
    b.reset()
    assert b.next() == 2.0


class FakeDb:
    def __init__(self, stores: list[UUID]) -> None:
        self.stores = stores

    @contextmanager
    def platform_transaction(self) -> Iterator[Any]:
        rows = [
            {"id": s, "name": "x", "whatsapp_group_id": None, "whatsapp_status": "OFFLINE"}
            for s in self.stores
        ]
        yield SimpleNamespace(execute=lambda *_a, **_k: SimpleNamespace(fetchall=lambda: rows))


class FakeSession:
    def __init__(self, store_id: UUID, new_device: bool) -> None:
        self.store_id, self.new_device = store_id, new_device
        self.running = False
        self.stopped = False

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False
        self.stopped = True


def test_manager_abre_so_lojas_com_sessao_e_nao_duplica() -> None:
    paired, unpaired = uuid4(), uuid4()
    created: list[FakeSession] = []

    def factory(store_id: UUID, new_device: bool) -> Any:
        s = FakeSession(store_id, new_device)
        created.append(s)
        return s

    manager = SessionManager(FakeDb([paired, unpaired]), factory, lambda sid: sid == paired, LOG)  # type: ignore[arg-type]
    assert not manager.synced
    assert manager.sync() == [paired]
    assert manager.synced and manager.running_count() == 1
    assert manager.sync() == []  # já rodando
    assert len(created) == 1 and not created[0].new_device


def test_manager_pair_e_stop_all() -> None:
    store = uuid4()
    created: list[FakeSession] = []

    def factory(store_id: UUID, new_device: bool) -> Any:
        s = FakeSession(store_id, new_device)
        created.append(s)
        return s

    manager = SessionManager(FakeDb([]), factory, lambda _sid: False, LOG)  # type: ignore[arg-type]
    assert manager.pair(store) and created[0].new_device
    assert not manager.pair(store)  # já rodando
    manager.stop_all()
    assert created[0].stopped and manager.running_count() == 0
