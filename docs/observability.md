# Observabilidade

## Health check

Servidor HTTP mínimo da biblioteca padrão (`src/pokemon_bot/trigger/health.py`), porta `HEALTH_PORT`
(padrão 8080):

- `GET /health`: liveness. 200 enquanto o processo está de pé.
- `GET /ready`: readiness. 200 quando o worker está pronto; 503 caso contrário. Hoje devolve 503
  fixo, porque o banco e o WhatsApp só entram nas fases 2 e 3.

## Logging estruturado

JSON, uma linha por evento (`src/pokemon_bot/logging_setup.py`), com `timestamp`, `level`,
`service`, `trace_id`, `message` e `context`.

**Nunca registrar** telefone, nome, CPF, token, conteúdo da sessão do WhatsApp nem texto de
mensagem de lance. Use identificadores internos (ids de loja e de leilão) e contagens. Exceções
saem só com o tipo, sem a mensagem, porque ela pode carregar dado pessoal. Falha ao resolver LID é
registrada sem o LID.

## Tracing (OpenTelemetry)

Adiado: o campo `trace_id` já existe no log. Ligar o SDK a `OTEL_EXPORTER_OTLP_ENDPOINT` quando o
Backend tiver coletor.
