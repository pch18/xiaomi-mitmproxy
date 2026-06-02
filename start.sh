#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi

requirements_hash="$(
    .venv/bin/python - <<'PY'
from hashlib import sha256
from pathlib import Path

print(sha256(Path("requirements.txt").read_bytes()).hexdigest())
PY
)"
marker=.venv/.xiaomi-mitmproxy-requirements-sha256

if [ ! -f "$marker" ] || [ "$(cat "$marker")" != "$requirements_hash" ]; then
    .venv/bin/python -m pip install -r requirements.txt
    printf '%s\n' "$requirements_hash" > "$marker"
fi

exec .venv/bin/python run.py "$@"
