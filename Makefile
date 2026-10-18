.PHONY: setup test lint format typecheck validate build run clean

# Fonte da verdade dos comandos: o CI (.github/workflows/ci.yml) e o Dockerfile só chamam estes alvos.
# Usa o ambiente virtual local (.venv) quando existir; no CI usa o python do runner.
PY := $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,$(if $(wildcard .venv/bin/python),.venv/bin/python,python))

setup: ## Instala o pacote e as ferramentas de desenvolvimento
	$(PY) -m pip install -e ".[dev]"

test: ## Testes com cobertura (relatório em coverage.xml)
	$(PY) -m pytest --cov --cov-report=term-missing --cov-report=xml

lint: ## Lint e formatação em modo check
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format: ## Formata o código
	$(PY) -m ruff check --fix .
	$(PY) -m ruff format .

typecheck: ## Checagem de tipos (mypy estrito)
	$(PY) -m mypy

validate: lint typecheck test ## Tudo que o CI exige

build: ## Valida que o pacote compila
	$(PY) -m compileall -q src

run: ## Sobe o worker localmente (precisa do .env)
	$(PY) -m pokemon_bot

clean: ## Remove artefatos
	rm -rf build dist coverage.xml .coverage .pytest_cache .mypy_cache .ruff_cache
