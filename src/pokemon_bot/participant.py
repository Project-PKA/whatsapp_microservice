"""Identificação do participante do grupo (ADR 0005 e risco do LID na ADR 0015).

A chave do cliente é o TELEFONE (`customers.phone`: só dígitos, com código do país, 8 a 15). Em
grupos o remetente pode vir como LID (identificador opaco). A ordem de tentativa:

1. `Sender`, se for telefone;
2. `SenderAlt`, se for telefone;
3. se algum dos dois for LID, a resolução LID -> telefone (no neonize, `get_pn_from_lid`).

Sem telefone, o resultado é `Unresolved`: o chamador registra o FATO (sem o LID, que é dado pessoal)
e não registra o lance, porque o cliente não poderia ser criado nem marcado no anúncio.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

PHONE_SERVER = "s.whatsapp.net"
LID_SERVER = "lid"

_DIGITS_RE = re.compile(r"[0-9]{8,15}")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2060\ufeff]")
MAX_NAME_LENGTH = 100


@dataclass(frozen=True)
class Address:
    """JID já separado em usuário e servidor (o gatilho converte do tipo do neonize)."""

    user: str
    server: str

    @property
    def is_lid(self) -> bool:
        return self.server == LID_SERVER


@dataclass(frozen=True)
class Participant:
    phone: str
    name: str


@dataclass(frozen=True)
class Unresolved:
    reason: Literal["missing", "lid_unresolved", "invalid"]


LidResolver = Callable[[Address], Address | None]


def normalize_phone(address: Address) -> str | None:
    """Telefone só com dígitos, sem sufixo de agente (`_1`) nem de dispositivo (`:69`)."""
    if address.server != PHONE_SERVER:
        return None
    user = address.user.split(":", 1)[0].split("_", 1)[0]
    if _DIGITS_RE.fullmatch(user) is None or user.startswith("0"):
        return None
    return user


def clean_display_name(raw: str | None) -> str | None:
    """Nome de exibição sem caracteres de controle e com tamanho limitado."""
    if raw is None:
        return None
    name = " ".join(_CONTROL_RE.sub("", raw).split())[:MAX_NAME_LENGTH]
    return name or None


def visitor_name(phone: str, display_name: str | None) -> str:
    """Nome do Visitante: o do WhatsApp, ou um rótulo neutro com o fim do número."""
    return clean_display_name(display_name) or f"Visitante {phone[-4:]}"


def identify_participant(
    sender: Address | None,
    sender_alt: Address | None,
    display_name: str | None,
    resolve_lid: LidResolver,
) -> Participant | Unresolved:
    candidates = [a for a in (sender, sender_alt) if a is not None and a.user]
    if not candidates:
        return Unresolved("missing")

    for address in candidates:
        phone = normalize_phone(address)
        if phone is not None:
            return Participant(phone, visitor_name(phone, display_name))

    lids = [a for a in candidates if a.is_lid]
    if not lids:
        return Unresolved("invalid")
    for lid in lids:
        phone = _resolve(lid, resolve_lid)
        if phone is not None:
            return Participant(phone, visitor_name(phone, display_name))
    return Unresolved("lid_unresolved")


def _resolve(lid: Address, resolve_lid: LidResolver) -> str | None:
    # Qualquer falha da resolução (rede, store do whatsmeow) vira "não resolvido", nunca exceção.
    try:
        resolved = resolve_lid(lid)
    except Exception:
        return None
    return normalize_phone(resolved) if resolved is not None else None
