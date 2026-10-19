# Moderação: remover participante em blacklist

## O que o bot faz

A cada minuto, por loja online, `Moderator.sweep`:

1. lê os telefones da blacklist (`customers.is_blacklisted`; o bot só enxerga o telefone, nunca o motivo);
2. lista os participantes do grupo (`get_group_info`);
3. remove quem está na blacklist (`update_group_participants` com `REMOVE`).

Regras de segurança, todas cobertas por teste:

- nunca remove administrador do grupo;
- no máximo 3 remoções por passada, com 8 a 20 segundos entre elas (`MODERATION_PACING`);
- até 3 tentativas por telefone; depois desiste e registra o fato uma vez (sem telefone no log);
- participante só com LID (sem telefone) não casa com a blacklist: é contado, não removido;
- o bot **nunca adiciona** participante (maior gatilho de ban, ADR 0015).

Lance de quem está na blacklist continua sem resposta no grupo (`CUSTOMER_BLACKLISTED`).

## O que NÃO foi verificado

A documentação do neonize não deixa claro e **não foi testado com conta real** (shared#31, item 8):

- se `update_group_participants(..., REMOVE)` funciona com o neonize 0.5.2;
- se o bot precisa ser administrador do grupo (o esperado: sim) e qual erro volta quando não é;
- se `GroupParticipant.PhoneNumber` vem preenchido em grupos com LID (senão a pessoa fica "sem telefone"
  e não é removida).

**Resultado do teste real:** pendente. Quando houver, registrar aqui (ou numa ADR no `shared`) o que
funcionou, o erro de quando o bot não é administrador e o que fazer com participantes só com LID.

## Fora do escopo desta fase

- Remoção por inatividade (`stores.inactivity_days_limit`): o `bot_runtime` não tem `SELECT` nessa
  coluna (pedido em shared#33).
- Enquete nativa do WhatsApp: decisão D18, fica de fora. O teto de `POLL` já é tratado pelo
  `place_bid` (`PAUSED_FOR_VALIDATION`) e o bot avisa o grupo.
