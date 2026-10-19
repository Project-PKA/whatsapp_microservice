from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from pokemon_bot.participant import Address
from pokemon_bot.trigger.whatsapp.convert import jid_to_address, message_text, to_incoming
from pokemon_bot.trigger.whatsapp.neonize_handle import NeonizeHandle
from pokemon_bot.trigger.whatsapp.pacing import PacingConfig


def jid(user: str, server: str = "s.whatsapp.net", device: int = 0) -> Any:
    return SimpleNamespace(User=user, Server=server, Device=device)


def strip_device(j: Any) -> Any:
    return SimpleNamespace(User=j.User, Server=j.Server, Device=0)


class Msg:
    def __init__(self, conversation: str = "", extended: str = "", protocol: bool = False) -> None:
        self.conversation = conversation
        self.extendedTextMessage = SimpleNamespace(text=extended)
        self._protocol = protocol

    def HasField(self, name: str) -> bool:
        return name == "protocolMessage" and self._protocol


def event(
    msg: Msg,
    *,
    group: bool = True,
    me: bool = False,
    edit: str = "",
    sender: Any = None,
    alt: Any = None,
    name: str = "Ash",
) -> Any:
    source = SimpleNamespace(
        IsGroup=group,
        IsFromMe=me,
        Sender=sender or jid("5511987654321", device=69),
        SenderAlt=alt or jid(""),
    )
    info = SimpleNamespace(MessageSource=source, ID="ABC", Pushname=name, Edit=edit)
    return SimpleNamespace(Info=info, Message=msg)


def test_texto_da_conversa_e_do_texto_estendido() -> None:
    assert message_text(Msg(conversation="#A41 50")) == "#A41 50"
    assert message_text(Msg(extended="#A41 60")) == "#A41 60"
    assert message_text(Msg()) == ""


def test_jid_vazio_vira_none_e_o_resto_vira_endereco() -> None:
    assert jid_to_address(jid(""), strip_device) is None
    assert jid_to_address(None, strip_device) is None
    assert jid_to_address(jid("123", "lid", 7), strip_device) == Address("123", "lid")


def test_evento_de_grupo_vira_mensagem() -> None:
    m = to_incoming(event(Msg(conversation="#A41 50")), strip_device)
    assert (m.message_id, m.is_group, m.is_from_me, m.is_edit, m.text) == (
        "ABC",
        True,
        False,
        False,
        "#A41 50",
    )
    assert m.sender == Address("5511987654321", "s.whatsapp.net")
    assert m.sender_alt is None and m.display_name == "Ash"


def test_edicao_e_revogacao_sao_marcadas() -> None:
    assert to_incoming(event(Msg(conversation="x"), edit="1"), strip_device).is_edit
    assert to_incoming(event(Msg(protocol=True)), strip_device).is_edit


def test_nome_vazio_vira_none() -> None:
    assert to_incoming(event(Msg(conversation="x"), name=""), strip_device).display_name is None


def test_sender_alt_e_preservado() -> None:
    m = to_incoming(event(Msg(), sender=jid("999", "lid"), alt=jid("5511987654321")), strip_device)
    assert m.sender == Address("999", "lid")
    assert m.sender_alt == Address("5511987654321", "s.whatsapp.net")


class FakeEvent:
    def __init__(self) -> None:
        self.handlers: dict[Any, Any] = {}
        self.qr_handler: Any = None

    def qr(self, f: Any) -> None:
        self.qr_handler = f

    def __call__(self, ev_type: Any) -> Any:
        def deco(f: Any) -> Any:
            self.handlers[ev_type.__name__] = f
            return f

        return deco


class FakeClient:
    def __init__(self, name: str, uuid: str, new_device: bool) -> None:
        self.args = (name, uuid, new_device)
        self.event = FakeEvent()
        self.sent: list[tuple[str, Any]] = []
        self.connected = False
        self.stopped = False

    def connect(self) -> None:
        self.connected = True

    def stop(self) -> None:
        self.stopped = True

    def send_message(self, to: Any, message: Any) -> None:
        self.sent.append(("msg", (to.User, to.Server, message)))

    def send_image(self, to: Any, path: str, caption: str) -> None:
        self.sent.append(("img", (to.User, path, caption)))

    def build_reaction(self, chat: Any, sender: Any, message_id: str, emoji: str) -> str:
        return f"reaction:{chat.User}:{sender.User}:{message_id}:{emoji}"

    def get_pn_from_lid(self, lid: Any) -> Any:
        return jid("5511987654321", device=3) if lid.User == "111" else jid("")


class Events:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def on_qr(self, data: bytes) -> None:
        self.calls.append(("qr", data))

    def on_connected(self) -> None:
        self.calls.append(("connected", None))

    def on_disconnected(self) -> None:
        self.calls.append(("disconnected", None))

    def on_logged_out(self) -> None:
        self.calls.append(("logged_out", None))

    def on_message(self, message: Any) -> None:
        self.calls.append(("message", message))


FAST = PacingConfig(max_per_minute=1000, min_gap=0.0, max_gap=0.0)


def _handle(clients: list[FakeClient], new_device: bool = False) -> NeonizeHandle:
    store = uuid4()

    def factory(name: str, uuid: str, new_device: bool) -> FakeClient:
        c = FakeClient(name, uuid, new_device)
        clients.append(c)
        return c

    return NeonizeHandle(
        "sessions/x.sqlite3",
        store,
        new_device=new_device,
        client_factory=factory,
        message_pacing=FAST,
        reaction_pacing=FAST,
    )


def test_run_registra_eventos_e_conecta() -> None:
    clients: list[FakeClient] = []
    handle = _handle(clients, new_device=True)
    events = Events()
    handle.run(events)
    client = clients[0]
    assert client.connected and client.args[0] == "sessions/x.sqlite3" and client.args[2] is True
    assert set(client.event.handlers) == {
        "Connected",
        "Disconnected",
        "LoggedOut",
        "Message",
    }
    client.event.qr_handler(client, b"qr")
    client.event.handlers["Connected"](client, None)
    client.event.handlers["Disconnected"](client, None)
    client.event.handlers["LoggedOut"](client, None)
    assert [c[0] for c in events.calls] == ["qr", "connected", "disconnected", "logged_out"]


def test_evento_de_mensagem_ilegivel_e_ignorado() -> None:
    clients: list[FakeClient] = []
    handle = _handle(clients)
    events = Events()
    handle.run(events)
    clients[0].event.handlers["Message"](clients[0], object())  # sem os atributos esperados
    assert events.calls == []


def test_envio_e_reacao_usam_o_chat_certo() -> None:
    clients: list[FakeClient] = []
    handle = _handle(clients)
    handle.run(Events())
    handle.send_text("120363012345678901@g.us", "oi")
    handle.send_image("120363012345678901@g.us", "foto.png", "legenda")
    handle.react("120363012345678901@g.us", "5511987654321@s.whatsapp.net", "ABC", "✅")
    sent = clients[0].sent
    assert sent[0] == ("msg", ("120363012345678901", "g.us", "oi"))
    assert sent[1] == ("img", ("120363012345678901", "foto.png", "legenda"))
    assert sent[2][1][2] == "reaction:120363012345678901:5511987654321:ABC:✅"


def test_resolve_lid() -> None:
    clients: list[FakeClient] = []
    handle = _handle(clients)
    handle.run(Events())
    assert handle.resolve_lid(Address("111", "lid")) == Address("5511987654321", "s.whatsapp.net")
    assert handle.resolve_lid(Address("222", "lid")) is None


def test_stop_antes_de_conectar_nao_quebra() -> None:
    _handle([]).stop()


@pytest.mark.parametrize("n", [0])
def test_stop_depois_de_conectar(n: int) -> None:
    clients: list[FakeClient] = []
    handle = _handle(clients)
    handle.run(Events())
    handle.stop()
    assert clients[0].stopped
