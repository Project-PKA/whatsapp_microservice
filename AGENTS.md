# AGENTS.md

> ⚠️ Este repositório é um **TEMPLATE**. Este arquivo, do jeito que
> está agora, descreve como um agente de IA deve se comportar *dentro
> do template*, não dentro de um serviço real gerado a partir dele.

## Se você é um agente de IA trabalhando neste repositório

**Primeiro passo, sempre:** verifique se existe um `BOOTSTRAP.md` na
raiz deste repositório.

- **Se existir:** leia e siga o `BOOTSTRAP.md` antes de qualquer outra
  coisa. Não gere código, não proponha arquitetura, não assuma stack
  ou tipo de gatilho até a entrevista nele estar completa.
- **Se não existir mais** (já foi apagado ao final do bootstrap): este
  é um serviço real, já configurado. Ignore o restante genérico deste
  arquivo e siga a versão **real** do `AGENTS.md`, gerada ao final do
  bootstrap, que deve conter:
  - Comandos reais de setup, lint, teste, build e run (não os
    placeholders do `Makefile` deste template).
  - Convenções reais de código da stack escolhida.
  - **A lista de tabelas/recursos externos que este serviço
    específico acessa** (banco compartilhado, filas, APIs externas —
    ver `docs/integration.md` e `ARCHITECTURE.md`), para que qualquer
    mudança respeite os limites de acesso documentados.

## Por que isso importa

Um agente de IA que ignora este arquivo e começa a escrever código
antes do bootstrap corre o risco de:
- Assumir uma stack ou um tipo de gatilho errado.
- Gerar um serviço com acesso mais amplo a banco compartilhado do que
  o necessário.
- Duplicar decisões de arquitetura que deveriam vir da entrevista, não
  de um palpite.
