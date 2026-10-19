"""QR no terminal, SÓ para desenvolvimento e pareamento feito pelo dono na própria máquina.

O QR dá acesso à conta de WhatsApp: nunca vai para log nem para arquivo. Em produção o QR precisa
de um canal até o painel, que ainda não existe (OWNER.md, D20).
"""

from __future__ import annotations

from uuid import UUID


class ConsoleQrSink:
    def publish(self, store_id: UUID, data: bytes) -> None:
        import segno  # vem junto com o neonize

        print(f"\nEscaneie no WhatsApp (loja {store_id}):", flush=True)
        segno.make_qr(data).terminal(compact=True)
