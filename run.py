"""Start the bundled Xiaomi mitmweb build."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vendor"))

from mitmproxy.tools.main import mitmweb  # noqa: E402


def main() -> None:
    args = [
        "-s",
        str(ROOT / "app.py"),
        "--listen-host",
        "0.0.0.0",
        "--listen-port",
        "8080",
        *sys.argv[1:],
    ]
    mitmweb(args)


if __name__ == "__main__":
    main()
