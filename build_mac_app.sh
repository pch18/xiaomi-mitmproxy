#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

python_path="$("$PYTHON_BIN" -c 'import sys; print(sys.executable)')"
python_arch="$(file "$python_path")"
if [[ "$python_arch" != *"x86_64"* || ( "$python_arch" != *"arm64"* && "$python_arch" != *"arm64e"* ) ]]; then
    cat >&2 <<EOF
Universal2 构建需要同时包含 x86_64 和 arm64 的 Python。

当前 Python:
  $python_path
  $python_arch

请使用 python.org 提供的 macOS universal2 Python 3.13，然后重新执行：
  PYTHON_BIN=/path/to/universal2/python3 ./build_mac_app.sh
EOF
    exit 1
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

venv_python_path="$("$VENV_DIR/bin/python" -c 'import sys; print(sys.executable)')"
venv_python_arch="$(file "$venv_python_path")"
if [[ "$venv_python_arch" != *"x86_64"* || ( "$venv_python_arch" != *"arm64"* && "$venv_python_arch" != *"arm64e"* ) ]]; then
    cat >&2 <<EOF
当前构建虚拟环境不是 universal2，无法构建 Intel + Apple Silicon 通用 App。

当前虚拟环境 Python:
  $venv_python_path
  $venv_python_arch

请删除旧的构建虚拟环境后，用 universal2 Python 重新构建：
  rm -rf "$VENV_DIR"
  PYTHON_BIN=/path/to/universal2/python3 VENV_DIR="$VENV_DIR" ./build_mac_app.sh
EOF
    exit 1
fi

"$VENV_DIR/bin/python" -m pip install -r requirements-build.txt
PYTHONPATH="$PWD/vendor:$PWD" "$VENV_DIR/bin/pyinstaller" --clean --noconfirm XiaomiMitmproxy.spec

printf '\nBuilt: %s\n' "$PWD/dist/Xiaomi Mitmproxy.app"
