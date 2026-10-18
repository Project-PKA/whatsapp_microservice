# Dependências

- **Fonte:** `pyproject.toml`, com versão exata (`==`) de tudo, inclusive `setuptools` do build.
- **Imagem Docker:** `requirements.txt`, com versão e hash dos wheels de Linux, instalado com
  `--only-binary :all: --require-hashes`. Assim nenhum `setup.py` de terceiro roda no build.
- **Aprovação:** dependência nova só com o ok do dono (versão, licença e motivo).

## Regenerar o `requirements.txt`

Resolva as dependências de runtime para Linux, baixe os wheels e calcule os hashes:

```bash
pip download --only-binary :all: --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64   --python-version 3.12 --implementation cp -d /tmp/wheels <dependências de runtime do pyproject>
pip hash /tmp/wheels/*.whl
```

Escreva uma linha `pacote==versão --hash=sha256:...` por wheel. Hoje não há dependência de runtime.
