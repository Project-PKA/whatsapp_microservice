# Imagem enxuta, multi-stage, usuário não-root. Dependências de runtime entram em pyproject.toml.
FROM python:3.12-slim AS build
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim AS run
WORKDIR /app
RUN useradd --system --create-home app
COPY --from=build /install /usr/local
USER app
# Porta do health check (docs/observability.md).
EXPOSE 8080
ENTRYPOINT ["python", "-m", "pokemon_bot"]
