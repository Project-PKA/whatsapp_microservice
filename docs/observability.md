# Observabilidade

> Este documento é um esqueleto de padrão, sem implementação nem lib
> específica ainda. A implementação real é feita na entrevista do
> [`BOOTSTRAP.md`](../BOOTSTRAP.md).

## Health check

Mesmo em serviços que não são HTTP (consumidor de fila, cron), este
serviço deve expor um endpoint auxiliar simples para health check,
usado por orquestradores/monitoramento.

- `GET /health` — liveness: o processo está de pé.
- `GET /ready` — readiness: o processo está pronto para receber
  trabalho (conexões com fila/banco estabelecidas, etc).

**TODO(bootstrap):** implementar os dois endpoints na porta `HEALTH_PORT`
(padrão 8080). Podem ser servidos por um servidor HTTP mínimo interno,
mesmo que o gatilho principal não seja HTTP. Os endpoints ficam fora de
versão (`/v1`) e sem autenticação: são contrato de infraestrutura.

## Logging estruturado

Todo log deve ser emitido em JSON, uma linha por evento, com pelo menos
os campos abaixo:

```json
{
  "timestamp": "2026-01-01T00:00:00.000Z",
  "level": "info",
  "service": "TODO-nome-do-servico",
  "trace_id": "TODO",
  "message": "descrição do evento",
  "context": { "chave": "valor" }
}
```

**TODO(bootstrap):** escolher a lib de logging da stack e configurar o
formato acima.

## Tracing distribuído (OpenTelemetry)

Este serviço deve propagar `trace_id`:

1. **Recebe** o `trace_id` de quem o chamou — extraído do header de
   propagação (requisição HTTP), de um atributo da mensagem (fila/evento),
   ou gerado no início da execução (cron, sem chamador).
2. **Anexa** o `trace_id` a todo log estruturado emitido durante o
   processamento (ver seção acima).
3. **Repassa** o `trace_id` adiante, se este serviço chamar outro
   serviço, publicar em outra fila, ou fizer uma chamada HTTP externa.

**TODO(bootstrap):** configurar o SDK de OpenTelemetry da stack
escolhida, apontando para `OTEL_EXPORTER_OTLP_ENDPOINT` (ver
[`.env.example`](../.env.example)).
