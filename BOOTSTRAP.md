# Bootstrap do serviço

> ⚠️ **Arquivo temporário.** Existe só até o setup inicial terminar. A etapa 9
> o apaga, junto com o `SETUP-GITHUB.md`, em um commit próprio.

Roteiro para transformar este template em um serviço real. Serve para uma
pessoa sozinha e como **instrução de trabalho para um agente de IA**.

> **Para o agente:** siga as etapas na ordem. Em cada uma, **faça as
> perguntas, espere a resposta, registre a decisão no arquivo indicado, e só
> então avance.** Recomende com trade-off explícito, mas não decida stack,
> gatilho ou acesso a banco por conta própria. **Não gere lógica de negócio
> antes da etapa 9.**

```
Leia o BOOTSTRAP.md e me conduza pelas etapas.
```

Comece com `make doctor`: ele mostra o que falta e os placeholders restantes.

**Já pronto e fora de discussão:** convenções (hooks + CI), governança, CI
completo com SonarCloud, agente do GitHub, release, deploy com build único
da imagem e os esqueletos de documentação.

---

## Etapa 1 — Responsabilidade única

**Pergunte:**

1. Em uma frase: o que este serviço faz, e o que ele deliberadamente **não**
   faz?
2. Por que isso é um serviço separado, e não um módulo do backend? (ciclo
   de deploy próprio, escala própria, isolamento de falha). Se não houver
   motivo, diga isso: pode ser melhor não criar o serviço.
3. Qual é o docs/shared do projeto (`org/repo`)?

**Registre em:** `ARCHITECTURE.md` "Responsabilidade única" · `AGENTS.md`
seção 1 · `README.md`

## Etapa 2 — Gatilho e comunicação

**Pergunte:**

1. Como ele é acionado: consumidor de fila/evento, cron ou HTTP? Pode ser
   uma combinação.
2. O que ele produz: mensagem publicada, resposta HTTP, escrita em banco,
   chamada a API externa?
3. Formato da mensagem/payload recebido e produzido. Se o formato cruza
   repositórios, a definição vai para o docs/shared (ADR ou schema).
4. Idempotência e falha: a mensagem pode chegar duas vezes? O que vai para
   retry, o que vai para dead-letter?

**Registre em:** [`docs/integration.md`](docs/integration.md) ·
`ARCHITECTURE.md` "Comunicação" e diagrama de integração

## Etapa 3 — Dados e recursos externos

**Pergunte:**

1. Tem banco próprio, ou acessa o banco de outro serviço?
2. Se compartilhado: quais tabelas, leitura ou escrita, e com que
   usuário/role **restrito**? As migrations dessas tabelas continuam no dono
   do schema (normalmente o backend), nunca aqui.
3. Que outras APIs e filas ele acessa?

**Registre em:** `docs/integration.md` (tabela de acesso) · `AGENTS.md`
seção 1 (a mesma lista) · `ARCHITECTURE.md`

## Etapa 4 — Volume e requisitos

**Pergunte:** mensagens/requisições por segundo, latência aceitável,
disponibilidade e criticidade (o que acontece se ele parar uma hora?).

**Registre em:** `ARCHITECTURE.md` "Decisões relevantes" · critério em `STACK.md`

## Etapa 5 — Stack

**Pergunte:** linguagem que o time domina, padrão da organização,
maturidade das libs para o gatilho escolhido e tamanho da imagem.

**Depois de decidir:**

1. Inicializar com a ferramenta oficial da stack.
2. `.tool-versions`; blocos da stack no `.gitignore` e no `dependabot.yml`.
3. `project.mk`: `SETUP_CMD`, `RUN_CMD`, `BUILD_CMD`, `CLEAN_CMD`,
   `BUILD_DIR`. Rode `make setup && make build`.
4. Commitar o lockfile.

**Registre em:** `STACK.md`

## Etapa 6 — Qualidade e testes

- `project.mk`: `LINT_CMD` (com code smells), `LINT_FIX_CMD`, `FORMAT_CMD`,
  `FORMAT_CHECK_CMD`, `TYPECHECK_CMD` (ou `skip` em linguagem compilada),
  `TEST_CMD`, `TEST_WATCH_CMD` e `TEST_COVERAGE_CMD` (grava em `coverage/`).
- **Pergunte:** como os testes de integração sobem fila e banco (containers
  efêmeros? fake em memória?) e qual o piso de cobertura.
- Escreva ao menos um teste de integração de verdade, por exemplo "mensagem
  válida é processada" e "mensagem malformada vai para a DLQ".

**Registre em:** `TESTING.md` · `STACK.md`

## Etapa 7 — Gatilho, health check e observabilidade

1. Implemente a camada de gatilho **isolada** (`docs/integration.md`).
2. Implemente `GET /health` e `GET /ready` na `HEALTH_PORT`, mesmo sem HTTP
   de negócio ([`docs/observability.md`](docs/observability.md)).
3. Logs JSON com `trace_id` **recebido** (header ou atributo da mensagem) e
   **repassado** adiante.
4. Graceful shutdown: ao receber SIGTERM, termine a mensagem em andamento.
5. **Serviço que expõe HTTP a outros:** configure `OPENAPI_CMD`, gere
   `docs/api/openapi.yaml`, ligue `contract-path` no `ci.yml` e acrescente
   `OPENAPI_CMD` a `REQUIRED_VARS` no Makefile. Senão, `OPENAPI_CMD = skip`.

## Etapa 8 — Container e deploy

1. `cp docker/Dockerfile.example Dockerfile`, preencher e validar com
   `docker build`.
2. Colar a entrada de `docker/compose.service.example` no compose de
   desenvolvimento do projeto.
3. **Pergunte:** onde roda (a mesma plataforma do backend, quase sempre) e
   quem opera.
4. Receita de [`DEPLOY.md`](DEPLOY.md) em `scripts/deploy.sh`; secrets no
   passo `Publicar` do `deploy.yml`.
5. Pedir para configurar `CODEQL_LANGUAGES` e os quatro Environments
   (`SETUP-GITHUB.md` B4 e B6).
6. Deploy em `dev` e confirmar que o serviço consome, roda ou responde.

**Registre em:** `DEPLOY.md` · `STACK.md`

## Etapa 9 — Fechamento

Nesta ordem. O `AGENTS.md` só é escrito quando os comandos **já rodam**.

1. Confira `STACK.md`, `ARCHITECTURE.md`, `TESTING.md`, `DEPLOY.md` e
   `docs/integration.md`.
2. `release-type` da stack em `release-please-config.json`; apague
   `version.txt` se o tipo novo não usar.
3. Troque os placeholders até `make doctor` não listar nenhum.
4. Rode o critério de pronto abaixo.
5. **Reescreva o `AGENTS.md`**: as sete seções, com a tabela de recursos
   externos da seção 1.
6. **Reescreva o `README.md`.**
7. `SETUP-GITHUB.md` parte B.
8. **Apague** `BOOTSTRAP.md` e `SETUP-GITHUB.md` em um commit próprio.
9. PR de teste: CI verde, agente comentando, PR de release depois do merge,
   deploy em `dev`.

### Critério de pronto

```bash
make doctor      # nenhum obrigatório pendente, nenhum placeholder
make validate
make build
docker build -t service:local .
```

- [ ] `/health` e `/ready` respondem, inclusive em worker sem HTTP
- [ ] A tabela de recursos externos bate com `docs/integration.md`
- [ ] Todo `skip` em `project.mk` é uma decisão registrada
- [ ] Deploy em `dev` funcionou; `homolog` para na aprovação
