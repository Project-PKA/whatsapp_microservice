<!--
Título do PR em Conventional Commits — ele vira a mensagem do squash merge:
  feat(consumer): trata reentrega de mensagem
  fix(cron): evita execucao dupla no mesmo intervalo
O CI valida título, commits e nome da branch.
-->

## O que muda

<!-- Uma ou duas frases. -->

## Por que

<!-- O motivo. Se já está na issue, aponte para ela em vez de repetir. -->

Closes #

## Como testar

<!-- Passo a passo para o revisor validar: a mensagem de exemplo publicada,
     o cron disparado à mão ou a requisição (curl/httpie). -->

1.
2.

## Tipo de mudança

- [ ] `feat` — funcionalidade nova
- [ ] `fix` — correção de bug
- [ ] `refactor` — muda o código sem mudar comportamento
- [ ] `perf` — melhora performance
- [ ] `docs` — só documentação
- [ ] `test` — só testes
- [ ] `build` / `ci` / `chore` — infra e ferramentas

## Checklist do autor

- [ ] `make validate` passa localmente
- [ ] Testes cobrindo o comportamento novo ou o bug corrigido
- [ ] **Fronteira mudou?** (formato de mensagem, contrato HTTP, recurso
      acessado) `docs/integration.md` e `AGENTS.md` seção 1 atualizados
- [ ] Mensagem malformada, reentrega e dependência fora do ar testadas,
      quando se aplica
- [ ] Variável de ambiente nova em `.env.example`, na leitura validada de
      ambiente e nas variables do GitHub Environment
- [ ] Sem log de depuração, teste marcado como `only`/`skip`, ou TODO sem issue
- [ ] Documentação atualizada quando o comportamento mudou
      (`ARCHITECTURE.md`, `AGENTS.md`, `README.md`)

## Esta mudança toca em autenticação, dados sensíveis ou entrada externa?

<!-- Entrada externa = input do usuário, upload, webhook, chamada a API de terceiro. -->

- [ ] Sim — preencha o checklist OWASP abaixo
- [ ] Não — pode apagar a seção abaixo

### Checklist OWASP Top 10 ([SECURITY.md](../SECURITY.md))

- [ ] Controle de acesso: autorização verificada em todo endpoint novo ou alterado
- [ ] Dados sensíveis: criptografia em trânsito/repouso; nenhum segredo ou PII em log
- [ ] Injection: toda entrada externa validada; SQL só parametrizado/via ORM
- [ ] Design seguro: rate limiting, timeouts, limite de tamanho de payload
- [ ] Configuração: headers, CORS e permissões padrão restritivas
- [ ] Dependências novas sem vulnerabilidade conhecida
- [ ] Autenticação e sessão seguem o padrão do `ARCHITECTURE.md`
- [ ] Integridade: webhooks com assinatura verificada; artefatos com checksum
- [ ] Eventos de segurança logados de forma estruturada, sem dado sensível
- [ ] SSRF: nenhuma requisição a URL/host vindo de entrada externa sem allowlist

## Risco e rollback

**Risco:** <!-- baixo / médio / alto -->

**Como reverter:** <!-- reimplantar o SHA anterior basta? mensagens processadas pela versão nova precisam de reprocessamento? -->

## Precisa de aprovação humana explícita?

<!-- Marque se o PR toca algo da seção 6 do AGENTS.md. -->

- [ ] Acessa recurso fora da tabela de `docs/integration.md`
- [ ] Escreve em banco compartilhado
- [ ] Muda formato de mensagem ou contrato HTTP de forma incompatível
- [ ] Muda autenticação entre serviços ou gestão de secrets
- [ ] Muda workflow de CI/CD, permissão de token ou `project.mk`
- [ ] Adiciona ou remove dependência
- [ ] Afrouxa regra de qualidade (lint, cobertura, `skip`)
- [ ] Nada acima
