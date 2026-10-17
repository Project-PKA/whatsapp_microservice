# BOOTSTRAP

> ⚠️ **Este arquivo é temporário.** Ele existe apenas até o setup
> inicial deste serviço estar completo. Ao final do processo abaixo,
> **apague este arquivo em um commit próprio** (`chore: remove
> BOOTSTRAP.md`), separado do commit que gera o resto dos artefatos.
>
> Se você é um agente de IA lendo este repositório: se este arquivo
> existe, siga-o antes de qualquer outra coisa — não gere código, não
> proponha arquitetura, não instale dependências antes de completar a
> entrevista abaixo.

## Entrevista

Faça as perguntas abaixo, **nesta ordem**, para a pessoa (ou time)
criando este serviço. Não avance para a próxima pergunta até a atual
estar respondida. **Não gere código nem arquitetura até todas as
perguntas relevantes estarem respondidas.**

1. **Qual a responsabilidade única deste serviço?** (uma frase — o que
   ele faz e o que ele deliberadamente não faz)
2. **Como ele se comunica com o resto do sistema?** (consumidor de
   fila/evento, worker agendado/cron, servidor HTTP simples, ou uma
   combinação — pode haver mais de um gatilho)
3. **Ele acessa banco de dados compartilhado com outro serviço?** Se
   sim, quais tabelas/schemas precisa ler e escrever?
4. **Qual o volume esperado e os requisitos de latência/disponibilidade?**
   (ex: quantas mensagens/req por segundo, SLA de resposta, criticidade)
5. **Qual a stack preferida?** (linguagem e, se já souber, framework/libs)

## Depois de responder tudo: o que gerar, nesta ordem

1. Instalar a stack escolhida (runtime, gerenciador de pacotes, linter,
   formatter, hook de pre-commit).
2. Substituir **todos** os placeholders `TODO(bootstrap)` em:
   - `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`,
     `.github/workflows/codeql.yml`, `.github/workflows/code-quality.yml`
   - `Dockerfile`
   - `docker-compose.yml`
   - `Makefile` (alvos `setup`, `test`, `lint`, `build`, `run`)
   - `.env.example`
3. Implementar a camada de gatilho escolhida (ver
   [`docs/integration.md`](docs/integration.md)), isolada em uma
   camada própria, e implementar os endpoints de health check (ver
   [`docs/observability.md`](docs/observability.md)).
4. Preencher [`STACK.md`](STACK.md), com a justificativa de cada
   escolha (pergunta 5, à luz da pergunta 4).
5. Preencher [`ARCHITECTURE.md`](ARCHITECTURE.md), incluindo o diagrama
   de integração (Mermaid) e, se houver banco compartilhado, a lista de
   tabelas/recursos acessados (pergunta 3) — mantendo essa lista em
   sincronia com `docs/integration.md`.
6. Preencher [`TESTING.md`](TESTING.md).
7. Gerar o `AGENTS.md` **real** deste serviço (seguindo a estrutura
   descrita no `AGENTS.md` atual deste template — comandos reais,
   convenções reais, e a lista de tabelas/recursos externos acessados).
8. **Apagar este arquivo (`BOOTSTRAP.md`)** em um commit próprio.
