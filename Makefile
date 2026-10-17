.PHONY: setup test lint build run

# Cada alvo abaixo é um placeholder. Na entrevista do BOOTSTRAP.md,
# substitua o comando de eco pelo comando real da stack escolhida.
# Este Makefile é a fonte da verdade usada pelo CI (.github/workflows/ci.yml)
# e pelo Dockerfile — evite duplicar comandos diretamente nos workflows.

setup: ## Instala dependências
	@echo "TODO(bootstrap): comando de install da stack escolhida" && exit 1

test: ## Roda a suíte de testes (ver TESTING.md)
	@echo "TODO(bootstrap): comando de testes da stack escolhida" && exit 1

lint: ## Roda lint + formatter em modo check
	@echo "TODO(bootstrap): comando de lint da stack escolhida" && exit 1

build: ## Compila/empacota o serviço
	@echo "TODO(bootstrap): comando de build da stack escolhida" && exit 1

run: ## Sobe o serviço localmente
	@echo "TODO(bootstrap): comando de run da stack escolhida" && exit 1
