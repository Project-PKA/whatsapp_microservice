# Imagem enxuta, multi-stage, usuário não-root.
# Dependências: só wheels, com versão e hash travados em requirements.txt (nada de setup.py de
# terceiros rodando no build). O código do bot entra por PYTHONPATH, sem instalar o pacote.
FROM python:3.12-slim AS build
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --only-binary :all: --require-hashes --target /deps -r requirements.txt

FROM python:3.12-slim AS run
WORKDIR /app
# libmagic: exigida pelo neonize (python-magic).
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --create-home app
COPY --from=build /deps /deps
COPY src ./src
ENV PYTHONPATH=/app/src:/deps PYTHONUNBUFFERED=1
USER app
# Porta do health check (docs/observability.md).
EXPOSE 8080
ENTRYPOINT ["python", "-m", "pokemon_bot"]
