# Estratégia de testes

O valor está em validar o **contrato**: o parser de lance (Backend e bot dependem dele), a leitura
do participante e o tratamento de cada `outcome` de `place_bid`.

## Unitários (sem WhatsApp, sem banco)

`tests/`. Eventos simulados. O parser tem testes por exemplo e por propriedade (hypothesis):
vírgula e ponto, `R$`, espaços, maiúsculas, lixo, mensagem editada.

## Integração

`tests/integration/`. Postgres real em contêiner efêmero (testcontainers), com as migrations do
Backend aplicadas (de `../Backend/migrations` ou de `BACKEND_MIGRATIONS_DIR`) e um login que
pertence ao grupo `bot_runtime`, **sem `BYPASSRLS`** (o superusuário só semeia, porque ignora o
RLS). Marcados com `@pytest.mark.integration`. **Pulados** (com o motivo) se faltar Docker ou a
migration `bot-runtime`; o CI do GitHub ainda não tem acesso ao Backend, então hoje roda só local. Cobrem: contexto `app.store_id` por transação, acesso cruzado entre
lojas negado e `place_bid` com cada `outcome`. Os contêineres criados nos testes são removidos.

## WhatsApp (fase 3 em diante)

Camada neonize atrás de uma interface própria; os testes usam um cliente falso. Conexão real só em
teste manual com a conta de teste (OWNER.md, A9), nunca no CI.

## Como rodar

```bash
make validate   # lint + tipos + testes com cobertura
```

Pré-requisitos: Python >= 3.10 e `make setup`. No Windows, instale o make
(`winget install ezwinports.make`) ou rode os comandos do `Makefile` à mão.

## Cobertura

Relatório em `coverage.xml` (lido pelo SonarCloud). Meta: o núcleo (`parser`, `participant`,
`reactions`, `templates`) perto de 100%; a camada de gatilho coberta pelos testes de integração.
