# Contrato de comunicação

## Tipo de gatilho

- [x] **Worker de longa duração**: um processo Python com um cliente WhatsApp (neonize) por loja.
      Reage a eventos do WhatsApp (mensagens do grupo) e a um laço de agenda (a cada minuto, por
      loja, chama `advance_auctions`).
- [x] **Servidor HTTP mínimo**: só `GET /health` e `GET /ready` (ver [`observability.md`](observability.md)).
- [ ] Consumidor de fila: não usa. Se o Backend precisar avisar o bot, isso vira ADR.

## Isolamento da camada de gatilho

Tudo que aciona o bot fica em `src/pokemon_bot/trigger/`. O núcleo (`parser`, `participant`,
`reactions`, `templates`) não importa neonize nem psycopg: recebe tipos próprios e devolve decisões.
Assim ele é testado com eventos simulados.

- Ponto de entrada: `python -m pokemon_bot` (`src/pokemon_bot/__main__.py`).
- Entrada: evento de mensagem do grupo, convertido para um tipo neutro (texto, remetente, nome de
  exibição, id da mensagem, se foi editada).
- Saída: efeitos no grupo (reação, resposta, carta, anúncio de vencedor) e escrita no banco.

## Banco de dados compartilhado

O bot acessa o **mesmo PostgreSQL** do Backend, com um papel próprio, **sem `BYPASSRLS` e nunca
superusuário**. Toda transação define `app.store_id` (`set_config(..., true)`, ADR 0011). O bot
**não tem migrations**: o schema é do Backend.

Papel definitivo: `bot_runtime` (pendente de aprovação do dono, OWNER.md D15). Até lá, o
desenvolvimento usa um papel provisório de teste, configurado só por `DATABASE_URL`.

### Funções (a regra mora no banco, ADR 0016)

| Função | Situação | Uso |
| --- | --- | --- |
| `place_bid(p_store_id, p_auction_id, p_customer_id, p_amount, p_raw_message, p_now)` | existe (migration 0013) | Registra o lance. O bot **não reimplementa** a regra |
| `advance_auctions(p_store_id, p_now)` | existe (migration 0013) | Abre, encerra, define vencedor e devolve a carta |
| `bot_set_whatsapp_status(...)` | **a pedir ao Backend** | Atualiza `stores.whatsapp_status` e `whatsapp_group_id` |
| achar-ou-criar Visitante por telefone | **a pedir ao Backend** | Cria `customers` (`is_visitor = true`), único por loja |
| leilão ativo por `short_code` | **a pedir ao Backend** | Resolve `#A41` para o leilão em andamento |

`place_bid` e `advance_auctions` são `SECURITY INVOKER`: rodam com os privilégios do chamador.
Portanto o `bot_runtime` precisa dos privilégios de tabela que elas usam (abaixo), além de
`EXECUTE`. Hoje o `EXECUTE` só foi dado a `app_runtime`.

### Tabelas

| Tabela | Operação | Motivo |
| --- | --- | --- |
| `stores` | leitura (`id`, `whatsapp_group_id`, `whatsapp_status`); escrita só via função | Saber quais lojas conectar e o grupo; publicar status |
| `customers` | leitura (`id`, `phone`, `is_blacklisted`, `name`); `UPDATE last_interaction_at` (efeito de `place_bid`); criação só via função | Identificar o participante, bloquear blacklist, criar Visitante |
| `cards_inventory` | leitura (`short_code`, `custom_photos`, `tcgdex_id`, `language`, `condition`, `status`); `UPDATE status` (efeito de `advance_auctions`) | Postar a carta e resolver o `#ID` |
| `auctions` | leitura; `UPDATE` (efeito de `place_bid` e `advance_auctions`) | Estado, horários, incremento, teto, vencedor |
| `bids` | leitura; `INSERT` (efeito de `place_bid`) | Maior lance, anunciar o vencedor |
| `whatsapp_sessions` | **decisão pendente** (ADR 0015: opção a ou b) | Sessão do dispositivo; é credencial |
| `tcgdex_catalog` | leitura | Nome da carta na legenda |

Esta lista deve acompanhar [`ARCHITECTURE.md`](../ARCHITECTURE.md). Mudar uma linha dela é mudança
de contrato e exige avisar o dono do Backend.

### Pendências conhecidas (com o Backend)

- **Modelos de mensagem por loja** (ADR 0006, "textos configuráveis"): não existe tabela nem coluna.
- **`short_code` e caixa**: a restrição aceita `A41` e `a41` como cartas diferentes. O bot tenta a
  correspondência exata e, se faltar, a sem diferenciar caixa quando for única.
- **Imagem da carta**: arquivos em `STORAGE_DIR/<loja>/<carta>/<uuid>.<ext>` no Backend.
