# template-microservice

Template **agnóstico de linguagem e de tipo de gatilho** para qualquer
microservice independente que eu crie dentro de um projeto (ex: um
worker que processa fila, um bot que integra com uma API externa, um
serviço HTTP simples). Não tem lógica de negócio nem exemplo funcional
de stack — cada serviço real decide isso na entrevista do
[`BOOTSTRAP.md`](BOOTSTRAP.md), não aqui.

Diferente de um template de backend completo, este é propositalmente
enxuto: sem camada de apresentação, muitas vezes sem framework web
completo.

## Como usar

1. No GitHub, clique em **"Use this template" → "Create a new
   repository"** — **não** dê fork. Isso cria um repositório novo, com
   histórico limpo, a partir deste template.
2. Clone o repositório novo criado.
3. Abra o [`BOOTSTRAP.md`](BOOTSTRAP.md) e siga a entrevista de ponta a
   ponta com um agente de IA (ou manualmente). Ela decide a stack, o
   tipo de gatilho e resolve todos os placeholders `TODO(bootstrap)`
   espalhados pelo repositório (workflows, `Dockerfile`,
   `docker-compose.yml`, `Makefile`, `.env.example`).
4. Ao final da entrevista, `BOOTSTRAP.md` é apagado e o
   [`AGENTS.md`](AGENTS.md) real do serviço é gerado.

Para convenções de código, comandos e o contrato de comunicação deste
serviço, **veja [`AGENTS.md`](AGENTS.md)** — este README não duplica
esse conteúdo.

## Estrutura

| Arquivo | Propósito |
|---|---|
| [`BOOTSTRAP.md`](BOOTSTRAP.md) | Entrevista de largada (apagado após o setup) |
| [`AGENTS.md`](AGENTS.md) | Como um agente de IA deve operar neste repositório |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Responsabilidade, integrações e diagrama do serviço |
| [`TESTING.md`](TESTING.md) | Estratégia de testes (foco em integração) |
| [`STACK.md`](STACK.md) | Justificativa da stack escolhida |
| [`docs/integration.md`](docs/integration.md) | Contrato de comunicação (gatilho, banco compartilhado) |
| [`docs/observability.md`](docs/observability.md) | Health check, logging, tracing |

## Configuração manual (somente via interface do GitHub)

Estes passos não podem ser automatizados por commit — precisam ser
feitos manualmente nas configurações do repositório no GitHub, uma vez
por repositório novo criado a partir deste template:

- [ ] **Marcar como Template Repository** — `Settings` → General →
      marcar "Template repository" (já deve estar marcado neste
      repositório-fonte; confirmar após qualquer mudança de nome/transfer).
- [ ] **Branch protection na `main`** — `Settings` → Branches → exigir
      PR review, exigir status checks (`CI`, `CodeQL`, `Code Quality`)
      antes de merge, exigir branch atualizada.
- [ ] **GitHub Environments** (`dev`, `staging`, `production`) —
      `Settings` → Environments → criar cada um, configurar secrets por
      ambiente e, para `production`, exigir approval manual (required
      reviewers).
- [ ] **Secret `SONAR_TOKEN`** — gerado no SonarCloud, adicionado em
      `Settings` → Secrets and variables → Actions.
- [ ] **Projeto criado no SonarCloud** e `sonar-project.properties`
      preenchido com `sonar.projectKey`/`sonar.organization` reais.
- [ ] **GitHub Project** para o repositório — criado, com a URL
      preenchida na variável `PROJECT_URL` (`Settings` → Secrets and
      variables → Actions → Variables) e um PAT com escopo `project`
      salvo como secret `GH_PROJECT_TOKEN`.
- [ ] **CODEOWNERS** — substituir o placeholder em
      [`.github/CODEOWNERS`](.github/CODEOWNERS) pelo usuário/time real.
- [ ] **Registry de imagem** (ghcr.io, ECR, Docker Hub...) — credenciais
      configuradas como secret, referenciadas em
      [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml).

Depois de configurar tudo, valide criando um serviço de exemplo via
"Use this template" e rodando a entrevista do `BOOTSTRAP.md` de ponta a
ponta, para confirmar que os placeholders ficam claros e fáceis de
resolver.
