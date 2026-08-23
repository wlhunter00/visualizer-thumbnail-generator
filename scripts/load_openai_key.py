#!/usr/bin/env python3
"""Resolve OPENAI_API_KEY without printing secret values.

Looks at (in order):
  1. The current process environment
  2. backend/.env (if it already defines a real key)
  3. Music Content connector secret JSON (api_key field)

Stdout is either empty or a single `export OPENAI_API_KEY=...` line for eval.
Stderr reports presence, length, and source only — never the key itself.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = REPO_ROOT / "backend" / ".env"
DEFAULT_CONNECTOR_JSON = Path(
    "/home/box/sand-data/connector-secrets/"
    "b2741e15-294d-43b2-954a-604f07a4561d/openai.json"
)
PLACEHOLDER_KEYS = frozenset({"", "sk-your-api-key-here"})


def is_real_key(value: Optional[str]) -> bool:
    if value is None:
        return False
    stripped = value.strip()
    return bool(stripped) and stripped not in PLACEHOLDER_KEYS


def read_dotenv_key(path: Path, name: str = "OPENAI_API_KEY") -> Optional[str]:
    if not path.is_file():
        return None
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() != name:
                continue
            return value.strip().strip("'").strip('"')
    except OSError:
        return None
    return None


def read_connector_key(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    key = data.get("api_key")
    if isinstance(key, str):
        return key.strip()
    return None


def resolve_openai_key(
    env: Optional[dict] = None,
    env_file: Path = DEFAULT_ENV_FILE,
    connector_json: Path = DEFAULT_CONNECTOR_JSON,
) -> Tuple[Optional[str], str]:
    """Return (key_or_none, source). Source is env, dotenv, connector, or missing."""
    environ = os.environ if env is None else env
    env_value = environ.get("OPENAI_API_KEY")
    if is_real_key(env_value):
        return env_value.strip(), "env"

    dotenv_value = read_dotenv_key(env_file)
    if is_real_key(dotenv_value):
        return dotenv_value.strip(), "dotenv"

    connector_value = read_connector_key(connector_json)
    if is_real_key(connector_value):
        return connector_value.strip(), "connector"

    return None, "missing"


def status_line(source: str, key: Optional[str]) -> str:
    if key and is_real_key(key):
        return f"OPENAI_API_KEY present source={source} len={len(key)}"
    return "OPENAI_API_KEY missing"


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Load OPENAI_API_KEY without printing it.")
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Print an export line on stdout when the key comes from the connector.",
    )
    args = parser.parse_args(argv)

    key, source = resolve_openai_key()
    print(status_line(source, key), file=sys.stderr)

    # Only emit an export when we actually pulled a connector secret.
    # env/dotenv are already available to the backend process.
    if args.eval and source == "connector" and key is not None:
        print(f"export OPENAI_API_KEY={shlex.quote(key)}")
    return 0 if source != "missing" else 1


if __name__ == "__main__":
    sys.exit(main())
