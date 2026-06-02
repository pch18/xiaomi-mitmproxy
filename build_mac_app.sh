#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi

.venv/bin/python -m pip install -r requirements-build.txt
PYTHONPATH="$PWD/vendor:$PWD" .venv/bin/pyinstaller --clean --noconfirm XiaomiMitmproxy.spec

printf '\nBuilt: %s\n' "$PWD/dist/Xiaomi Mitmproxy.app"
