# Docker

Exemplos, não configuração ativa. O template não sabe qual é a stack, e um
`Dockerfile` quebrado na raiz faria o CI falhar em todo PR sem dizer por quê.

| Arquivo | Para quê |
| --- | --- |
| `Dockerfile.example` | Imagem do serviço: copie para `./Dockerfile` e preencha |
| `compose.service.example` | Entrada para colar no compose de desenvolvimento do **projeto** |

## Como usar

```sh
cp docker/Dockerfile.example Dockerfile
# troque os TODO(bootstrap) pelos comandos de project.mk
docker build -t service:local .
docker run --rm --env-file .env -p 8080:8080 service:local
curl -fsS localhost:8080/health
```

Depois disso, o CI (job "Imagem Docker") valida o build em todo PR, e o
`deploy.yml` publica a imagem no GHCR no push em `main`. Quando a raiz
tiver o `Dockerfile`, apague esta pasta.

## Configuração em runtime

A imagem é a mesma de `dev` a `prod`. URLs de fila, banco e APIs chegam por
variável de ambiente no deploy, e nunca por `ARG`/`ENV` gravado na imagem.
