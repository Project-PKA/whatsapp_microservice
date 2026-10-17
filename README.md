# template-microservice

Template **agnóstico de linguagem e de gatilho** para qualquer serviço
independente de um projeto: um worker que processa fila, um cron, um bot que
integra com uma API externa, um serviço HTTP simples. Não tem lógica de
negócio nem stack. Cada serviço decide isso no [`BOOTSTRAP.md`](BOOTSTRAP.md).

É propositalmente mais enxuto que o template de backend: sem camada de
apresentação, sem banco próprio por padrão, com foco na **fronteira** de
comunicação com o resto do sistema.

## Como usar

1. No GitHub: **Use this template → Create a new repository** (não fork).
2. Clone e peça ao agente de IA (ou siga sozinho):

   ```
   Leia o BOOTSTRAP.md e me conduza pelas etapas.
   ```

   Abra o Claude Code **dentro deste repositório**, com o docs/shared do
   projeto clonado ao lado e acessível (no terminal:
   `claude --add-dir ../<projeto>-shared`). O `CLAUDE.md` daqui é carregado
   no início, e o agente lê as decisões de sistema de lá.

   São nove etapas: responsabilidade única, gatilho e comunicação, dados e
   recursos externos, volume, stack, qualidade e testes, health check e
   observabilidade, deploy, fechamento.
3. `make doctor` mostra o que falta; [`SETUP-GITHUB.md`](SETUP-GITHUB.md)
   lista o que só se configura na interface do GitHub.

Depois do bootstrap, o [`AGENTS.md`](AGENTS.md) descreve o serviço real,
inclusive **a lista de recursos externos que ele pode acessar**.

## O que vem pronto

- **Contrato de comandos** `Makefile` + `project.mk`: CI e hooks não sabem a
  stack; um alvo não configurado falha com instrução, e `skip` é uma
  decisão registrada.
- **CI** com um único check de merge (`ci-success`): convenções, formato,
  lint, tipos, testes com cobertura, build, imagem Docker e SonarCloud.
- **Build once, deploy many:** imagem única no GHCR (tag = SHA), promovida
  por `dev` → `test` → `homolog` → `prod` com aprovação.
  [`DEPLOY.md`](DEPLOY.md) tem as receitas e o graceful shutdown.
- **Release** automática (release-please), CodeQL, Dependabot e o agente do
  GitHub.
- **Fronteira documentada:** [`docs/integration.md`](docs/integration.md)
  (gatilho, formato de mensagem, tabela de acesso a banco compartilhado) e
  [`docs/observability.md`](docs/observability.md) (health check mesmo sem
  HTTP, logs JSON, `trace_id` propagado).

| Arquivo | Para que serve |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Contexto para pessoas e agentes. **Comece por aqui.** |
| [`BOOTSTRAP.md`](BOOTSTRAP.md) | Entrevista de largada (apagado após o setup) |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Responsabilidade, integrações e diagrama do serviço |
| [`STACK.md`](STACK.md) · [`TESTING.md`](TESTING.md) | Escolhas e estratégia de testes |
| [`DEPLOY.md`](DEPLOY.md) · [`SECURITY.md`](SECURITY.md) | Deploy e segurança |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Fluxo de contribuição |

## Requisitos

`git`, `make` e Docker; `mise`/`asdf` é recomendado. **Windows:**
`winget install ezwinports.make` ou WSL.

## Manutenção do template

As convenções vêm do `CONVENCOES.md` do `codex-base`. O que é política comum
(CI, convenções, agente, release) mora nos workflows centrais `@v1`, e o
resto é cópia: serviços já criados não recebem atualização automática.
