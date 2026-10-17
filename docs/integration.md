# Contrato de comunicação

> Este documento é um esqueleto. O tipo de gatilho real deste serviço é
> decidido na entrevista do [`BOOTSTRAP.md`](../BOOTSTRAP.md) e
> preenchido aqui ao final dela.

## Tipo de gatilho

Este serviço é acionado por um (ou uma combinação) dos seguintes tipos.
**TODO(bootstrap): marcar o(s) escolhido(s) e remover os demais.**

- [ ] **Consumidor de fila/evento** — reage a mensagens publicadas por
      outro sistema (ex: SQS, RabbitMQ, Kafka, pub/sub).
- [ ] **Worker agendado (cron)** — executa em intervalos programados,
      sem depender de um evento externo.
- [ ] **Servidor HTTP simples** — expõe endpoints HTTP mínimos, sem
      camada de apresentação.

## Isolamento da camada de gatilho

Independentemente do tipo escolhido, a implementação do gatilho deve
ficar isolada em uma camada própria (ex: `internal/trigger`,
`src/trigger`, `cmd/worker` — nome real definido no bootstrap), para
deixar claro no código onde fica a fronteira de comunicação entre este
serviço e o resto do sistema. O restante do código não deve saber se
foi chamado por uma fila, um cron ou um request HTTP.

**TODO(bootstrap):** documentar aqui:
- O ponto de entrada real (arquivo/pasta).
- O formato da mensagem/evento/payload recebido (schema, exemplo).
- O que este serviço produz como saída (mensagem publicada, resposta
  HTTP, efeito colateral).

## Contratos que cruzam repositórios

Formato de evento/mensagem consumido ou produzido por **outro** repositório é
contrato público: a definição (schema, exemplo, versão) fica no docs/shared
do projeto (ADR ou arquivo de schema), e este documento aponta para lá.
Mudança incompatível exige versão nova do evento ou migração coordenada, e
nunca "troca e vê o que quebra".

Se este serviço **expõe HTTP** a outros serviços, o contrato é gerado do
código (`make openapi` → `docs/api/openapi.yaml`) e o CI o valida quando
`contract-path` está ligado no `ci.yml`.

**TODO(bootstrap):** link do contrato no docs/shared, ou "não cruza repositórios".

## Banco de dados compartilhado

Se este serviço acessar um banco de dados de outro repositório/serviço
(em vez de um banco próprio), isso é uma exceção que precisa de
documentação explícita e de acesso restrito ao mínimo necessário.

**TODO(bootstrap), se aplicável:**

| Tabela/schema | Operação (leitura/escrita) | Motivo |
|---|---|---|
| `TODO` | `TODO` | `TODO` |

Esta tabela deve ser mantida em sincronia com a seção de comunicação em
[`ARCHITECTURE.md`](../ARCHITECTURE.md) e com a tabela de recursos da seção 1
do [`AGENTS.md`](../AGENTS.md). As migrations dessas tabelas vivem **só** no
dono do schema (normalmente o backend). O acesso ao banco deve ser
restrito (usuário/role dedicado) ao conjunto mínimo de tabelas listado
acima.
