# AGENTS.md

## Leia primeiro

1. [`../shared/OWNER.md`](../shared/OWNER.md): canal com o dono. Se um item dele bloqueia a tarefa,
   pare e avise. O que depender do dono vai lá e numa issue em `Project-PKA/shared`.
2. [`../shared/ARCHITECTURE.md`](../shared/ARCHITECTURE.md), [`../shared/GLOSSARY.md`](../shared/GLOSSARY.md)
   e as ADRs 0003, 0004, 0005, 0006, 0007, 0011, 0013, 0015 e 0016 em `../shared/docs/adr/`.

## O que é

Worker Python (>= 3.10) com neonize: um cliente WhatsApp por loja. Lê lances `#ID valor` no grupo,
registra com a função `place_bid` do PostgreSQL do Backend, posta a carta ao abrir o leilão e marca
o vencedor no grupo ao encerrar. **Não** reimplementa regra de lance, **não** manda mensagem privada
automática e **não** adiciona participantes por API.

## Comandos

```bash
make setup       # pip install -e ".[dev]"
make lint        # ruff check + ruff format --check
make typecheck   # mypy estrito
make test        # pytest com cobertura (coverage.xml)
make validate    # lint + typecheck + test (o que o CI exige)
make run         # python -m pokemon_bot
```

Sem `make` (Windows): rode os comandos do `Makefile` com o Python do `.venv`.

## Convenções

- **Identificadores em inglês; comentários e mensagens ao usuário em português.** Termos de domínio
  do [`GLOSSARY.md`](../shared/GLOSSARY.md) (`short_code`, `customer`, `auction`), sem sinônimos.
- mypy estrito e ruff (inclui complexidade); nenhuma função acima de complexidade 10.
- Dinheiro é `Decimal`, nunca `float`.
- O núcleo (`parser`, `participant`, `reactions`, `templates`) não importa neonize nem psycopg. O que
  aciona o bot fica em `src/pokemon_bot/trigger/`.
- **Nunca logar** telefone, nome, CPF, token, conteúdo da sessão nem texto de mensagem de lance.
- **Nenhuma exceção escapa** de um callback do whatsmeow: todo handler fica em try/except.
- Segredo nunca em código, issue ou PR. `.env`, `.env.*.local` e arquivos de sessão estão no `.gitignore`.
- A sessão do WhatsApp é credencial: o administrador da plataforma não a lê (ADR 0012).
- Commits em Conventional Commits; branches `feature/`, `fix/`, `chore/`, `docs/`, `test/`,
  `refactor/`. PR em rascunho. **Nunca** merge sem o dono dizer, nunca force push, nunca mexer em
  branch protection, Environments ou secrets.
- Pergunte antes de adicionar dependência (versão, licença e motivo). Aprovadas até agora: ruff,
  mypy, pytest, pytest-cov, hypothesis e testcontainers (dev); psycopg, psycopg-binary e psycopg-pool
  (runtime). Pendente: neonize (fase 3).

## Banco: tabelas e funções acessadas

Fonte da verdade: [`docs/integration.md`](docs/integration.md). Resumo:

- **Funções:** `place_bid`, `advance_auctions`, `bot_set_whatsapp_status`.
- **Tabelas (por coluna):** `stores`, `customers`, `cards_inventory`, `auctions`, `bids`,
  `tcgdex_catalog` e `whatsapp_sessions` (só estado de conexão, D17 opção a).
- Papel: grupo `bot_runtime` (migration 0021 do Backend), **sem `BYPASSRLS`**. Toda transação define `app.store_id`.
  Em teste de RLS, nunca superusuário. Não altere o Backend: abra issue lá com o pedido exato.
- Mudar essa lista é mudança de contrato: atualize `docs/integration.md` e `ARCHITECTURE.md`.

## Docker

Ao usar Docker nos testes, apague os contêineres que você criar.
