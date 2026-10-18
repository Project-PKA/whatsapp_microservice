# Dependências

- **Fonte:** `pyproject.toml`, com versão exata (`==`) de tudo, inclusive `setuptools` do build.
- **Imagem Docker:** `requirements.txt`, com versão e hash dos wheels de Linux, instalado com
  `--only-binary :all: --require-hashes`. Assim nenhum `setup.py` de terceiro roda no build.
- **Aprovação:** dependência nova só com o ok do dono (versão, licença e motivo).

## `pylock.toml`

Travamento completo (runtime e dev) no formato PEP 751, com hash, para **Linux x86_64 e Python 3.12**
(o ambiente do CI e da imagem). Regenere a cada mudança em `pyproject.toml`:

```bash
make lock
```

O `pip lock` ainda é experimental e trava só a plataforma em que roda; por isso o `make lock` usa um
contêiner Linux. No Windows, instale por `pip install -e ".[dev]"` (versões exatas do `pyproject.toml`).

## `requirements.txt`

Só as dependências de runtime, com versão e hash (`--require-hashes`). O `make lock` também o
regenera a partir do `pyproject.toml` (`scripts/pylock_to_requirements.py`). Não edite à mão.
