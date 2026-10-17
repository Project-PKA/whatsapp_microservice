# Estratégia de testes

> Esqueleto a ser preenchido na entrevista do [`BOOTSTRAP.md`](BOOTSTRAP.md).

Este serviço não tem camada de apresentação, então o foco de testes é
diferente de um serviço backend tradicional: o valor está em validar o
**contrato de comunicação** (ver [`docs/integration.md`](docs/integration.md))
e o comportamento diante de dependências externas (fila, banco, API).

## Testes unitários

**TODO(bootstrap):** o que é testado isoladamente (regras de negócio,
transformação de dados), sem dependências externas reais.

## Testes de integração

O ponto central deste documento. **TODO(bootstrap):** para cada
dependência externa deste serviço, descrever como ela é testada:

- **Fila/evento** — TODO: consumidor real contra um broker local
  (container docker-compose) ou fake/in-memory? Como simular
  mensagem malformada, reentrega, dead-letter?
- **Banco (próprio ou compartilhado)** — TODO: banco real em container
  efêmero, migração aplicada antes da suíte rodar?
- **API externa** — TODO: mock de contrato (ex: WireMock, Pact) ou
  gravação/replay de requisições reais?

## Como rodar

```bash
make test
```

**TODO(bootstrap):** pré-requisitos (containers, variáveis de ambiente)
para rodar a suíte de integração localmente e no CI.

## Cobertura

**TODO(bootstrap):** meta de cobertura, se houver, e como ela é
reportada (ver `.github/workflows/ci.yml` e `.github/workflows/code-quality.yml`).
