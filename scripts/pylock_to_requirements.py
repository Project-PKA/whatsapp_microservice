"""Converte `runtime.lock.toml` (PEP 751) em `requirements.txt` com hashes (`pip --require-hashes`).

Sem argumentos: lê e escreve sempre na raiz do repositório (o `make lock` roda daqui).
Ignora o próprio projeto (entrada de diretório, sem wheel). Só entram pacotes com wheel e hash.
"""

from __future__ import annotations

from pathlib import Path

import tomllib

LOCK_FILE = "runtime.lock.toml"
OUTPUT_FILE = "requirements.txt"
HEADER = """# Dependências de RUNTIME da imagem Docker, travadas com versão e hash (Linux, Py 3.12).
# GERADO por `make lock` a partir do pyproject.toml. Não edite à mão (docs/dependencias.md)."""


def convert(lock: dict[str, object]) -> str:
    lines = [HEADER]
    packages = lock.get("packages", [])
    assert isinstance(packages, list)
    for package in sorted(packages, key=lambda p: str(p["name"])):
        wheels = package.get("wheels")
        if not wheels:
            continue
        hashes = sorted({str(w["hashes"]["sha256"]) for w in wheels})
        line = f"{package['name']}=={package['version']}"
        lines.append(line + " \\\n    " + " \\\n    ".join(f"--hash=sha256:{h}" for h in hashes))
    return "\n".join(lines) + "\n"


def main() -> None:
    lock = tomllib.loads(Path(LOCK_FILE).read_text(encoding="utf-8"))
    Path(OUTPUT_FILE).write_text(convert(lock), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
