# =============================================================================
# COMANDOS DO SERVICO
#
# Este e o unico arquivo que voce preenche para ligar a fundacao a sua stack.
# O `Makefile` (que voce nao edita) e o CI so conhecem os nomes abaixo.
#
# Tres estados possiveis para cada variavel:
#
#   vazio   -> nao configurado. O alvo FALHA com instrucao. E o estado inicial.
#   skip    -> nao se aplica a este servico. O alvo passa, avisando.
#   comando -> executado como esta, no shell.
#
# Use `skip` de forma consciente: ele e uma decisao registrada
# ("worker de fila, sem API HTTP publica"), nao um esquecimento.
# `make doctor` mostra os tres estados de uma vez.
# =============================================================================

# -----------------------------------------------------------------------------
# Ciclo de desenvolvimento
# -----------------------------------------------------------------------------

# Instala dependencias de forma reprodutivel (lockfile obrigatorio no CI).
SETUP_CMD =

# Sobe o servico localmente, com o gatilho escolhido (docs/integration.md).
RUN_CMD =

# Compila/empacota. Linguagem interpretada sem build? Use um comando que
# valide o pacote ou `skip`.
BUILD_CMD =

CLEAN_CMD =

BUILD_DIR = dist

# -----------------------------------------------------------------------------
# Qualidade — o lint DEVE cobrir code smells/complexidade.
# -----------------------------------------------------------------------------

LINT_CMD =
LINT_FIX_CMD =
FORMAT_CMD =
FORMAT_CHECK_CMD =

# `skip` em linguagem compilada (o build ja checa tipos).
TYPECHECK_CMD =

# -----------------------------------------------------------------------------
# Testes — foco em integracao com fila/banco/API externa (TESTING.md).
# -----------------------------------------------------------------------------

TEST_CMD =
TEST_WATCH_CMD =

# Grava o relatorio em coverage/ (lcov.info de preferencia).
TEST_COVERAGE_CMD =

# -----------------------------------------------------------------------------
# Contrato de API — so para servico que EXPOE HTTP a outros servicos.
# Worker de fila/cron: `skip`. Servico HTTP: gere docs/api/openapi.yaml do
# codigo e ligue `contract-path` no ci.yml.
# -----------------------------------------------------------------------------

OPENAPI_CMD =

# =============================================================================
# EXEMPLOS — copie, ajuste e descomente o bloco da sua stack.
# =============================================================================

# ---- Node + TypeScript (worker de fila) -----------------------------------
# SETUP_CMD          = npm ci --no-audit --no-fund
# RUN_CMD            = npm run dev
# BUILD_CMD          = npm run build
# LINT_CMD           = npx eslint . --max-warnings=0
# LINT_FIX_CMD       = npx eslint . --fix
# FORMAT_CMD         = npx prettier --write .
# FORMAT_CHECK_CMD   = npx prettier --check .
# TYPECHECK_CMD      = npx tsc --noEmit
# TEST_CMD           = npx vitest run
# TEST_WATCH_CMD     = npx vitest
# TEST_COVERAGE_CMD  = npx vitest run --coverage --coverage.reporter=lcov
# OPENAPI_CMD        = skip

# ---- Python (uv) -----------------------------------------------------------
# SETUP_CMD          = uv sync --frozen
# RUN_CMD            = uv run python -m app.worker
# BUILD_CMD          = uv build
# LINT_CMD           = uv run ruff check .
# FORMAT_CHECK_CMD   = uv run ruff format --check .
# TYPECHECK_CMD      = uv run mypy app
# TEST_CMD           = uv run pytest
# TEST_COVERAGE_CMD  = uv run pytest --cov=app --cov-report=lcov:coverage/lcov.info
# OPENAPI_CMD        = skip

# ---- Go --------------------------------------------------------------------
# SETUP_CMD          = go mod download
# RUN_CMD            = go run ./cmd/worker
# BUILD_CMD          = go build -o $(BUILD_DIR)/worker ./cmd/worker
# LINT_CMD           = golangci-lint run
# FORMAT_CHECK_CMD   = test -z "$$(gofmt -l .)"
# TYPECHECK_CMD      = skip
# TEST_COVERAGE_CMD  = mkdir -p coverage && go test ./... -coverprofile=coverage/coverage.out
# OPENAPI_CMD        = skip
