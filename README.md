# whatsapp_microservice

Bot de WhatsApp do **pokemonAuction** (nome provisório): uma sessão por loja, lê os lances no grupo
(`#ID valor`), registra pela função `place_bid` do banco, posta a carta e anuncia o vencedor.

Python >= 3.10 e neonize ([ADR 0015](../shared/docs/adr/0015-bot-em-python-com-neonize.md)). Acessa o
mesmo PostgreSQL do Backend com papel próprio e RLS.

## Começando

```bash
python -m venv .venv
make setup      # instala o pacote e as ferramentas de dev
make validate   # lint, tipos e testes
make run        # sobe o worker (precisa do .env, veja .env.example)
```

Para ver o sistema inteiro rodando junto: `docker compose up -d --build` em `../shared`.

## Documentação

| Arquivo | Conteúdo |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Regras para agentes de IA e convenções |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Responsabilidade, integração e estrutura |
| [`STACK.md`](STACK.md) | Por que esta stack |
| [`TESTING.md`](TESTING.md) | Estratégia de testes |
| [`docs/integration.md`](docs/integration.md) | Tabelas e funções do banco que o bot acessa |
| [`docs/observability.md`](docs/observability.md) | Health, logs e o que nunca logar |
| [`docs/spike/`](docs/spike/) | Spike do dono com neonize (referência, não é código de produção) |

Decisões que atravessam repositórios ficam em [`../shared/docs/adr/`](../shared/docs/adr/). O canal
com o dono é [`../shared/OWNER.md`](../shared/OWNER.md).
