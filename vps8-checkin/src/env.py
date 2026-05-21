"""Local environment file support.

The production path (GitHub Actions) provides real environment variables.
For local debugging, this module loads .env.local/.env from the project root
without overriding values that are already exported by the shell.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILES = (".env.local", ".env")


def load_local_env() -> list[str]:
    loaded: list[str] = []

    for filename in ENV_FILES:
        path = PROJECT_ROOT / filename
        if not path.exists():
            continue

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue

            value = _strip_inline_comment(value.strip())
            os.environ[key] = _unquote(value)
            loaded.append(key)

    return loaded


def _strip_inline_comment(value: str) -> str:
    if not value or value[0] in ("'", '"'):
        return value

    marker = value.find(" #")
    if marker == -1:
        return value
    return value[:marker].rstrip()


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value
