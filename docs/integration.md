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
O acesso ao banco fica em `db.py` e `repository.py`.

- Ponto de entrada: `python -m pokemon_bot` (`src/pokemon_bot/__main__.py`).
- Entrada: evento de mensagem do grupo, convertido para `IncomingMessage`.
- Saída: efeitos no grupo (reação, resposta, carta, anúncio de vencedor) e escrita no banco.

## Banco de dados compartilhado

O bot acessa o **mesmo PostgreSQL** do Backend com um login que pertence ao grupo **`bot_runtime`**
(`NOLOGIN`, sem `BYPASSRLS`, nunca superusuário), criado pela **migration 0021 do Backend**
(OWNER.md D15, Backend#98). A conexão vem só da `DATABASE_URL`. Toda transação define
`app.store_id` (`set_config(..., true)`, ADR 0011), exceto a listagem de lojas. O bot **não tem
migrations**: o schema é do Backend.

> A migration 0021 estava na branch `feature/papel-bot-runtime` do Backend quando esta fase foi
> escrita; os testes de integração a exigem e são pulados se ela não existir.

### Funções (a regra mora no banco, ADR 0016)

| Função | Uso |
| --- | --- |
| `place_bid(p_store_id, p_auction_id, p_customer_id, p_amount, p_raw_message, p_now)` | Registra o lance. O bot **não reimplementa** a regra |
| `advance_auctions(p_store_id, p_now)` | Abre, encerra, define vencedor e devolve a carta |
| `bot_set_whatsapp_status(p_store_id, p_status, p_group_id)` | `SECURITY DEFINER`: atualiza `stores.whatsapp_status` e `whatsapp_group_id` da loja do contexto |

`place_bid` e `advance_auctions` são `SECURITY INVOKER`: usam os privilégios de tabela do
`bot_runtime`, que a migration 0021 concede por coluna.

### Tabelas e colunas

| Tabela | Operação | Motivo |
| --- | --- | --- |
| `stores` | `SELECT (id, name, whatsapp_group_id, whatsapp_status)`, sem contexto de loja; escrita só pela função | Saber quais sessões abrir |
| `whatsapp_sessions` | `SELECT, INSERT, UPDATE, DELETE` da loja do contexto | Só o estado de conexão (D17, opção a: a sessão do neonize fica em Postgres próprio do bot) |
| `customers` | `SELECT (id, store_id, phone, name, is_visitor, is_blacklisted, last_interaction_at)`; `INSERT (store_id, phone, name)`; `UPDATE (last_interaction_at)` | Achar ou criar o Visitante (ADR 0005); sem CPF, e-mail nem endereço |
| `cards_inventory` | `SELECT (id, store_id, short_code, tcgdex_id, language, condition, is_foil, custom_photos, notes, status)`; `UPDATE (status, updated_at)` (efeito de `advance_auctions`) | Resolver o `#ID` e montar a legenda |
| `auctions` | `SELECT`; `UPDATE (status, winning_bid_id, max_value_reached_alert)` (efeito das funções) | Estado, horários, incremento, teto, vencedor |
| `bids` | `SELECT, INSERT` | Maior lance e anúncio do vencedor |
| `tcgdex_catalog` | `SELECT (id, name, card_number, set_name, set_id, raw_data)` | Nome e imagem da carta |

Esta lista deve acompanhar [`ARCHITECTURE.md`](../ARCHITECTURE.md). Mudar uma linha dela é mudança
de contrato e exige avisar o dono do Backend.

### Pendências conhecidas (com o Backend)

- **Modelos de mensagem por loja** (ADR 0006, "textos configuráveis"): não existe tabela nem coluna.
  Enquanto isso valem os padrões de `templates.py`.
- **`short_code` e caixa**: a restrição aceita `A41` e `a41` como cartas diferentes. O bot tenta a
  correspondência exata e, se faltar, a sem diferenciar caixa quando for única.
- **Imagem da carta**: arquivos em `STORAGE_DIR/<loja>/<carta>/<uuid>.<ext>` no Backend, montados
  no bot como volume somente leitura (D19).
- **Telefone**: números brasileiros sem o nono dígito podem não casar com `normalizePhone` do Backend.
