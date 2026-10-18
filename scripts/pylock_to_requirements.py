"""Converte um pylock.toml (PEP 751) em requirements.txt com hashes, para `pip --require-hashes`.

Uso: python scripts/pylock_to_requirements.py <pylock.toml> <requirements.txt>

Ignora o próprio projeto (entrada de diretório, sem wheel). Só entram pacotes com wheel e hash.
"""

from __future__ import annotations

import sys
from pathlib import Path

import tomllib

HEADER = """# Dependências de RUNTIME da imagem Docker, travadas com versão e hash (Linux, Py 3.12).
# GERADO por `make lock` a partir do pyproject.toml. Não edite à mão (docs/dependencias.md).
"""


def convert(lock: dict[str, object]) -> str:
    lines = [HEADER.rstrip("\n")]
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


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    lock = tomllib.loads(Path(argv[1]).read_text(encoding="utf-8"))
    Path(argv[2]).write_text(convert(lock), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
