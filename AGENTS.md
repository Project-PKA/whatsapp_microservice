# AGENTS.md

> **Este arquivo pertence a um repositório TEMPLATE.**
>
> Se você está lendo isto dentro de um serviço criado a partir do template,
> **este arquivo está desatualizado por definição**, e reescrevê-lo é a sua
> primeira tarefa.

---

## Para agentes de IA: leia isto antes de qualquer coisa

### Se este repositório ainda É o template

Você está no `template-microservice`: a fundação de qualidade, CI/CD e
documentação de todo serviço independente de um projeto, seja um worker de
fila, um cron ou um serviço HTTP simples.

Ele **não tem stack nem gatilho**, de propósito. A fundação conversa com a
stack pelo contrato `Makefile` + `project.mk`.

- **Não adicione stack** (`go.mod`, `package.json`...) nem lógica de negócio.
- Mudanças válidas: workflow, esqueleto de documentação, regra, receita de
  deploy, exemplo em `project.mk`.
- Convenções (branches, ambientes, labels, secrets) vêm do `CONVENCOES.md`
  do `codex-base`. Não invente outras aqui.

### Se este repositório FOI CRIADO a partir do template

**Antes de escrever qualquer código, conduza o bootstrap:**
[`BOOTSTRAP.md`](BOOTSTRAP.md). Rode `make doctor` primeiro.

Não assuma stack nem tipo de gatilho, e não dê a este serviço acesso mais
amplo a banco compartilhado do que o documentado. Essas decisões vêm da
entrevista, não de palpite.

**A última etapa do bootstrap é reescrever este arquivo** seguindo o modelo
abaixo. Apague tudo acima da linha `<!-- INICIO DO MODELO -->`, preencha e
commite sozinho (`docs: define AGENTS.md do servico`).

### Faxina do primeiro commit

| Arquivo | O que fazer |
| --- | --- |
| `AGENTS.md`, `README.md` | Reescrever para o serviço |
| `BOOTSTRAP.md`, `SETUP-GITHUB.md` | Apagar depois de concluir |
| `project.mk`, `.tool-versions` | Preencher |
| `STACK.md`, `ARCHITECTURE.md`, `TESTING.md`, `DEPLOY.md`, `docs/integration.md` | Preencher os esqueletos |
| `docker/Dockerfile.example` | Copiar para `./Dockerfile`, preencher e apagar a pasta `docker/` |
| `.github/CODEOWNERS`, `sonar-project.properties`, `.github/ISSUE_TEMPLATE/config.yml` | Trocar os placeholders de organização e repositório (`make doctor` lista) |
| `release-please-config.json` | Trocar `release-type` pelo da stack |
| `scripts/deploy.sh` | Implementar com a receita de `DEPLOY.md` |

**Não remova:** `Makefile`, `.githooks/`, `scripts/` (convenções), os
workflows, `CLAUDE.md`, os arquivos do release-please.

---

<!-- INICIO DO MODELO — em um servico real, tudo acima disto sai -->

## Estrutura obrigatória do AGENTS.md do serviço

Sete seções, nesta ordem. O que está entre `<!-- -->` é instrução e sai.

---

### 1. Visão geral

<!--
Em até 10 linhas:
  - A responsabilidade ÚNICA deste serviço, e o que ele deliberadamente NÃO faz.
  - O gatilho (fila X, cron Y, HTTP) e o que ele produz.
  - Estágio (protótipo, produção) e criticidade.
-->

**docs/shared do projeto:** <!-- org/repo, ou "não há" -->. Antes de decisão de
arquitetura, de contrato ou de formato de evento, leia o `ARCHITECTURE.md`,
as ADRs e o `GLOSSARY.md` de lá, de preferência clonado ao lado
(`../<nome-do-shared>`).

**Recursos externos que este serviço acessa.** Esta lista é o limite: acessar
algo fora dela exige aprovação humana (seção 6). Ela espelha o
[`docs/integration.md`](docs/integration.md).

| Recurso | Tipo | Operação | Observação |
| --- | --- | --- | --- |
| <!-- fila pedidos.criados --> | <!-- fila --> | <!-- consome --> | <!-- DLQ: ... --> |
| <!-- tabela orders (banco do backend) --> | <!-- banco compartilhado --> | <!-- leitura --> | <!-- role svc_x_ro --> |

### 2. Comandos

| Comando | O que faz | Observação |
| --- | --- | --- |
| `make setup` | Instala dependências e ativa os hooks | Primeira coisa após o clone |
| `make run` | Sobe o serviço com o gatilho | <!-- dependências: fila/banco locais --> |
| `make build` | Compila/empacota | |
| `make lint` / `make format` / `make typecheck` | Qualidade | |
| `make test` | Unitários + integração | <!-- containers necessários --> |
| `make test-coverage` | Com cobertura | Mínimo <!-- % --> |
| `make validate` | Formato + lint + tipos + testes | **Rode antes de abrir PR** |
| `make doctor` | O que está configurado e o que falta | |

**Windows:** `winget install ezwinports.make` ou WSL.

### 3. Convenções

<!--
Regras verificáveis. Sugestões:
**Fronteira** — o código de gatilho fica isolado em <pasta>; o resto não sabe
  se foi chamado por fila, cron ou HTTP.
**Idempotência** — toda mensagem pode chegar mais de uma vez; como o serviço
  deduplica.
**Erros** — o que vai para retry, o que vai para DLQ, o que é descartado.
**Logs** — JSON com trace_id recebido da mensagem/request.
**Configuração** — leitura de ambiente em um único módulo, validada no boot.
-->

### 4. Regras de commit e PR

**Branches:** `feature/`, `fix/`, `hotfix/`, `release/`, `chore/`, `docs/`,
`refactor/` ou `test/` + slug em minúsculas.
**Commits:** Conventional Commits (`feat(consumer): trata reentrega`). Os
tipos são `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore` e `revert`.

- O título do PR também segue Conventional Commits, porque vira o commit em
  `main` e entra no CHANGELOG.
- Vincule a issue com `Closes #N`. PR pequeno.
- Merge só com `ci-success` verde e aprovação de CODEOWNER.

### 5. Checklist de conclusão de tarefa

- [ ] `make validate` passa
- [ ] Teste de integração cobrindo o comportamento novo (mensagem
      malformada, reentrega e dependência fora do ar, quando se aplicar)
- [ ] `docs/integration.md` e a tabela da seção 1 atualizados se o contrato
      de comunicação ou os recursos acessados mudaram
- [ ] Variável de ambiente nova em `.env.example` e no GitHub Environment
- [ ] Nenhum log de depuração, segredo ou teste `skip`

### 6. Pontos que exigem aprovação humana

- Acessar recurso que **não** está na tabela da seção 1 (tabela nova, fila
  nova, API nova)
- Mudar formato de mensagem/evento ou contrato HTTP de forma incompatível
- Escrever em tabela de banco compartilhado
- Adicionar, remover ou trocar dependência
- Mudar `project.mk`, workflows, permissão de token ou regra de deploy
- Rodar deploy para `homolog` ou `prod`
- Afrouxar regra de qualidade; apagar teste ou marcá-lo como `skip`
- `git push --force` ou reescrita de histórico
- Qualquer coisa que envolva dado real de usuário

### 7. Armadilhas conhecidas

- <!-- -->

---

## Como a fundação funciona (referência)

| Peça | Papel |
| --- | --- |
| `Makefile` / `project.mk` | Contrato de comandos / os comandos reais da stack |
| `scripts/conventions.sh` + `.githooks/` | Regras de branch e commit nos hooks locais |
| `.github/workflows/ci.yml` | Portão de merge (`ci-success`) |
| `.github/workflows/deploy.yml` + `scripts/deploy.sh` | Build único da imagem e promoção entre ambientes |
| `.github/workflows/release.yml` | Versão e CHANGELOG (release-please) |
| `.github/workflows/github-agent.yml` | Feedback no PR e nas issues; nunca bloqueia |
| `IgorOCosta/workflows` (`@v1`) | Lógica dos workflows e regras centrais de convenção |
| `CLAUDE.md` | `@AGENTS.md`, para o Claude Code carregar este arquivo |
