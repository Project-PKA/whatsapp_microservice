# Stack

| Escolha | Alternativas consideradas | Por que esta e não as outras |
| --- | --- | --- |
| Linguagem: Python >= 3.10 | Node.js + Baileys (ADR 0007, substituída) | Escolha do dono (ADR 0015); o neonize é Python e o núcleo puro é fácil de testar |
| Cliente WhatsApp: neonize (fase 3) | Baileys, API oficial da Meta | Escolha do dono; sobre o whatsmeow (Go). A API oficial cobra por conversa e limita grupos (ADR 0007) |
| Banco: psycopg 3 (fase 2) | asyncpg, SQLAlchemy | Só chama funções e lê poucas tabelas; sem ORM, e a regra mora no banco (ADR 0016) |
| Lint e formatação: ruff | flake8 + black | Uma ferramenta só; inclui complexidade (C90) |
| Tipos: mypy estrito | pyright | Padrão do ecossistema; falha no CI |
| Testes: pytest, pytest-cov, hypothesis | unittest | Propriedades do parser, que é contrato com o Backend |
| Log: `logging` da biblioteca padrão, formatador JSON próprio | structlog | Sem dependência; o formato é simples |
| Health: `http.server` | FastAPI | Dois endpoints; não justifica framework |

Dependências de runtime hoje: psycopg 3, psycopg-binary e psycopg-pool (LGPL-3.0), aprovadas pelo
dono. testcontainers (Apache-2.0) só nos testes. Entram com aprovação do dono, uma fase por vez.
