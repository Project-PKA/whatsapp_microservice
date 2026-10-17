# Esqueleto de imagem enxuta, multi-stage. Preencher na entrevista do
# BOOTSTRAP.md de acordo com a stack escolhida. O objetivo é manter a
# imagem final a menor possível (sem toolchain de build, sem
# dependências de dev) e rodando como usuário não-root.

# ---- Estágio de build -------------------------------------------------
# TODO(bootstrap): trocar pela imagem base da stack escolhida
# (ex: golang:1.23-alpine, node:22-alpine, python:3.13-slim).
FROM TODO-base-image AS build

WORKDIR /app
COPY . .

# TODO(bootstrap): comando de install de dependências da stack
RUN echo "TODO(bootstrap): install de dependencias" && exit 1

# TODO(bootstrap): comando de build/compilação da stack
RUN echo "TODO(bootstrap): build" && exit 1

# ---- Estágio final -----------------------------------------------------
# TODO(bootstrap): trocar pela menor imagem runtime possível
# (ex: gcr.io/distroless/static, alpine, scratch para binários estáticos).
FROM TODO-runtime-image AS run

WORKDIR /app

# Roda como usuário não-root.
# TODO(bootstrap): ajustar se a imagem base já tiver um usuário próprio.
RUN addgroup -S app && adduser -S app -G app
USER app

COPY --from=build /app/TODO-artefato-de-build ./

# Porta usada pelo health check auxiliar (ver docs/observability.md).
# TODO(bootstrap): confirmar/ajustar a porta.
EXPOSE 8080

# TODO(bootstrap): comando real de start do serviço.
ENTRYPOINT ["echo", "TODO(bootstrap): comando de start"]
