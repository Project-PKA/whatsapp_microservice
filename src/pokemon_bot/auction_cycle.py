"""Ciclo do leilão no grupo: virar o estado pelo relógio, abrir (carta) e encerrar (vencedor).

A virada de estado é do banco (`advance_auctions`, que o job do Backend também chama a cada
minuto). Por isso o bot NÃO anuncia só o que ele mesmo virou: a cada passada ele olha o que já
abriu ou já encerrou e ainda não foi anunciado.

O que já foi anunciado fica no banco (`bot_opened_announced_at` e `bot_closed_announced_at` em
`auctions`, migration 0023 do Backend), então um reinício não repete anúncio. A janela (`window`)
só evita anunciar leilão antigo na primeira passada depois de ligar o bot. Se o envio falha, o
marcador não é gravado e a próxima passada tenta de novo; se o bot cair entre enviar e gravar, o
anúncio pode sair uma vez a mais (entrega pelo menos uma vez).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID

from pokemon_bot import repository
from pokemon_bot.db import Database
from pokemon_bot.repository import AuctionRow, FinishedRow
from pokemon_bot.templates import format_money, render, resolve_template
from pokemon_bot.trigger.whatsapp.ports import ClientHandle

Kind = Literal["opened", "closed"]
# Horário de Brasília. O Brasil não tem horário de verão desde 2019; evita depender do tzdata.
BRT = timezone(timedelta(hours=-3))


def format_deadline(moment: datetime) -> str:
    return moment.astimezone(BRT).strftime("%d/%m às %H:%M")


def photo_path(storage_dir: Path | None, store_id: UUID, auction: AuctionRow) -> Path | None:
    """Primeira foto da carta no volume somente leitura (`STORAGE_DIR/<loja>/<carta>/<arquivo>`)."""
    if storage_dir is None:
        return None
    for name in auction.photos:
        # O id guardado é `<uuid>.<ext>`; recusa qualquer coisa com cara de caminho.
        if isinstance(name, str) and name and Path(name).name == name:
            candidate = storage_dir / str(store_id) / str(auction.card_id) / name
            if candidate.is_file():
                return candidate
    return None


class AuctionCycle:
    def __init__(
        self,
        db: Database,
        logger: logging.Logger,
        *,
        storage_dir: Path | None = None,
        templates_for: Callable[[UUID], Mapping[str, str] | None] = lambda _store: None,
        window: timedelta = timedelta(minutes=15),
    ) -> None:
        self._db = db
        self._log = logger
        self._storage_dir = storage_dir
        self._templates_for = templates_for
        self._window = window

    def tick(
        self, store_id: UUID, group_id: str, client: ClientHandle, now: datetime | None = None
    ) -> None:
        """Uma passada da loja: avança o relógio e anuncia o que abriu e o que encerrou."""
        moment = now or datetime.now(timezone.utc)
        since = moment - self._window
        with self._db.store_transaction(store_id) as conn:
            repository.advance_auctions(conn, store_id, moment)
            started = repository.list_started_unannounced(conn, store_id, since, moment)
            finished = repository.list_finished_unannounced(conn, store_id, since)
        templates = self._templates_for(store_id)
        for auction in started:
            self._announce_open(store_id, group_id, client, auction, templates)
        for row in finished:
            self._announce_close(store_id, group_id, client, row, templates)

    def _mark(self, store_id: UUID, auction_id: UUID, kind: Kind) -> None:
        """Grava o marcador no banco; se falhar, só registra (o próximo ciclo reenvia)."""
        try:
            with self._db.store_transaction(store_id) as conn:
                repository.mark_announced(conn, store_id, auction_id, kind)
        except Exception as error:
            self._log.error(
                "falha ao gravar o marcador de anúncio",
                extra={"context": {"kind": kind, "error": type(error).__name__}},
            )

    def _guard(self, what: str, action: Callable[[], None]) -> bool:
        try:
            action()
        except Exception as error:
            # Não marca como anunciado: tenta de novo na próxima passada.
            self._log.error(
                "falha ao anunciar",
                extra={"context": {"what": what, "error": type(error).__name__}},
            )
            return False
        return True

    def _announce_open(
        self,
        store_id: UUID,
        group_id: str,
        client: ClientHandle,
        auction: AuctionRow,
        templates: Mapping[str, str] | None,
    ) -> None:
        caption = render(
            resolve_template("card_opened", templates),
            {
                "card": auction.card_name,
                "short_code": auction.short_code,
                "initial_bid": format_money(auction.initial_bid),
                "min_increment": format_money(auction.min_increment),
                "ends_at": format_deadline(auction.end_time),
            },
        )
        photo = photo_path(self._storage_dir, store_id, auction)

        def send() -> None:
            if photo is not None:
                client.send_image(group_id, str(photo), caption)
            else:
                client.send_text(group_id, caption)

        if self._guard("open", send):
            self._mark(store_id, auction.auction_id, "opened")

    def _announce_close(
        self,
        store_id: UUID,
        group_id: str,
        client: ClientHandle,
        row: FinishedRow,
        templates: Mapping[str, str] | None,
    ) -> None:
        auction = row.auction
        values = {"card": auction.card_name, "short_code": auction.short_code}
        if row.winner_phone is None or row.winning_amount is None:
            text = render(resolve_template("auction_unsold", templates), values)
        else:
            text = render(
                resolve_template("auction_won", templates),
                {
                    **values,
                    # O WhatsApp marca a pessoa pelo `@número` no texto (ADR 0006).
                    "winner": f"@{row.winner_phone}",
                    "amount": format_money(row.winning_amount),
                },
            )
        if self._guard("close", lambda: client.send_text(group_id, text)):
            self._mark(store_id, auction.auction_id, "closed")
