"""Native macOS launcher for the bundled Xiaomi mitmproxy build."""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

APP_NAME = "Xiaomi Mitmproxy"
WEB_HOST = "127.0.0.1"
DEFAULT_PROXY_PORT = 8080
MAIN_WINDOW_WIDTH = 1024
MAIN_WINDOW_HEIGHT = 600
WEB_TOKEN = "xiaomi-mitmproxy-local"
DATA_DIR_ENV = "XIAOMI_MITMPROXY_DATA_DIR"


@dataclass
class ServerRuntime:
    proxy_port: int
    web_port: int
    master: Any | None = None
    error: Exception | None = None
    stopped: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None

    @property
    def web_url(self) -> str:
        return f"http://{WEB_HOST}:{self.web_port}/?token={WEB_TOKEN}"


def _bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _data_dir() -> Path:
    path = Path.home() / "Library" / "Application Support" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _lan_address() -> str:
    try:
        route = subprocess.run(
            ["/sbin/route", "-n", "get", "default"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        interface = next(
            line.split(":", 1)[1].strip()
            for line in route.stdout.splitlines()
            if line.strip().startswith("interface:")
        )
        address = subprocess.run(
            ["/usr/sbin/ipconfig", "getifaddr", interface],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()
        if address:
            return address
    except (OSError, StopIteration, subprocess.SubprocessError):
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def _window_title(proxy_port: int) -> str:
    return f"{APP_NAME}  [ Proxy Address = {_lan_address()}:{proxy_port} ]"


def _resize_main_window_centered(window: Any) -> None:
    x = window.x - (MAIN_WINDOW_WIDTH - window.width) // 2
    y = window.y - (MAIN_WINDOW_HEIGHT - window.height) // 2
    window.move(x, y)
    window.resize(MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)


def _port_is_available(host: str, port: int) -> bool:
    targets = [WEB_HOST] if host in ("0.0.0.0", "::") else [host]
    for target in targets:
        try:
            with socket.create_connection((target, port), timeout=0.2):
                return False
        except OSError:
            continue
    return True


def _find_free_web_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((WEB_HOST, 0))
        return sock.getsockname()[1]


def _server_args(runtime: ServerRuntime) -> list[str]:
    return [
        "-s",
        str(_bundle_root() / "app.py"),
        "--listen-host",
        "0.0.0.0",
        "--listen-port",
        str(runtime.proxy_port),
        "--web-host",
        WEB_HOST,
        "--web-port",
        str(runtime.web_port),
        "--set",
        "web_open_browser=false",
        "--set",
        f"web_password={WEB_TOKEN}",
    ]


def _configure_logging() -> None:
    log_path = _data_dir() / "xiaomi-mitmproxy.log"
    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)


async def _serve(runtime: ServerRuntime) -> None:
    from mitmproxy import exceptions
    from mitmproxy import optmanager
    from mitmproxy import options
    from mitmproxy.tools import cmdline
    from mitmproxy.tools import main as tools_main
    from mitmproxy.tools.web import master as web_master

    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("tornado").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)
    logging.getLogger("urwid").setLevel(logging.INFO)
    logging.getLogger("quic").setLevel(logging.WARNING)

    opts = options.Options()
    master = web_master.WebMaster(opts)
    runtime.master = master
    parser = cmdline.mitmweb(opts)
    args = parser.parse_args(_server_args(runtime))

    try:
        opts.set(*args.setoptions, defer=True)
        optmanager.load_paths(
            opts,
            os.path.join(opts.confdir, "config.yaml"),
            os.path.join(opts.confdir, "config.yml"),
        )
        tools_main.process_options(parser, opts, args)
    except exceptions.OptionsError as exc:
        raise RuntimeError(str(exc)) from exc

    await master.run()


def _run_server(runtime: ServerRuntime) -> None:
    try:
        asyncio.run(_serve(runtime))
    except Exception as exc:
        runtime.error = exc
        logging.exception("Xiaomi Mitmproxy server stopped with an error")
    finally:
        runtime.stopped.set()


def _start_server(proxy_port: int) -> ServerRuntime:
    os.environ[DATA_DIR_ENV] = str(_data_dir())
    _configure_logging()
    runtime = ServerRuntime(proxy_port=proxy_port, web_port=_find_free_web_port())
    runtime.thread = threading.Thread(
        target=_run_server,
        args=(runtime,),
        name="xiaomi-mitmproxy-server",
        daemon=True,
    )
    runtime.thread.start()
    return runtime


def _wait_until_ready(runtime: ServerRuntime, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if runtime.stopped.is_set():
            raise RuntimeError("抓包服务启动失败，请检查日志文件。") from runtime.error
        try:
            with urllib.request.urlopen(runtime.web_url, timeout=0.5):
                return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.1)
    raise RuntimeError("抓包服务启动超时，请检查日志文件。")


async def _shutdown_master(master: Any) -> None:
    await master.proxyserver.servers.update([])
    master.shutdown()


def _stop_server(runtime: ServerRuntime | None) -> None:
    if runtime is None:
        return
    if runtime.master is not None:
        if (
            runtime.thread is not None
            and runtime.thread.is_alive()
            and runtime.thread is not threading.current_thread()
        ):
            try:
                future = asyncio.run_coroutine_threadsafe(
                    _shutdown_master(runtime.master),
                    runtime.master.event_loop,
                )
                future.result(timeout=5)
            except Exception:
                logging.exception("Failed to close proxy listeners cleanly")
                runtime.master.shutdown()
        else:
            runtime.master.shutdown()
    if runtime.thread is not None and runtime.thread is not threading.current_thread():
        runtime.thread.join(timeout=5)


def _request_server_stop(runtime: ServerRuntime | None) -> None:
    if runtime is None or runtime.master is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(
            _shutdown_master(runtime.master),
            runtime.master.event_loop,
        )
    except Exception:
        logging.exception("Failed to request proxy listener shutdown")
        runtime.master.shutdown()


PORT_FORM_HTML = """\
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 48px; color: #222; }
    form { display: flex; gap: 10px; align-items: center; }
    input { font-size: 16px; padding: 8px; width: 120px; }
    button { background: #396cad; border: 0; border-radius: 4px; color: white; padding: 10px 16px; }
    #message { color: #b42318; margin-top: 18px; white-space: pre-wrap; }
  </style>
</head>
<body>
  <h2>设置手机代理端口</h2>
  <p>请输入手机需要连接的代理端口：</p>
  <form id="port-form">
    <input id="port" type="number" min="1" max="65535" value="8080" autofocus required>
    <button type="submit">启动抓包</button>
  </form>
  <div id="message"></div>
  <script>
    document.getElementById("port-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const message = document.getElementById("message");
      message.textContent = "正在启动…";
      const result = await window.pywebview.api.start(document.getElementById("port").value);
      if (!result.ok) message.textContent = result.error;
    });
  </script>
</body>
</html>
"""


class PortApi:
    def __init__(self) -> None:
        self.window: Any | None = None
        self.runtime: ServerRuntime | None = None
        self.closed = threading.Event()
        self.lock = threading.Lock()

    def start(self, value: str) -> dict[str, object]:
        try:
            proxy_port = int(value)
            if not 1 <= proxy_port <= 65535:
                raise ValueError("端口必须在 1 到 65535 之间。")
            if not _port_is_available("0.0.0.0", proxy_port):
                raise ValueError(f"端口 {proxy_port} 已被占用，请输入其他端口。")
            runtime = _start_server(proxy_port)
            _wait_until_ready(runtime)
            with self.lock:
                if self.closed.is_set():
                    raise RuntimeError("应用窗口已关闭。")
            self.runtime = runtime
            assert self.window is not None
            _resize_main_window_centered(self.window)
            self.window.title = _window_title(proxy_port)
            self.window.load_url(runtime.web_url)
            return {"ok": True}
        except Exception as exc:
            _stop_server(locals().get("runtime"))
            return {"ok": False, "error": str(exc)}

    def stop(self) -> None:
        self.closed.set()
        with self.lock:
            runtime, self.runtime = self.runtime, None
        _stop_server(runtime)

    def copy_text(self, value: object) -> dict[str, object]:
        try:
            _copy_text_to_macos("" if value is None else str(value))
            return {"ok": True}
        except Exception as exc:
            logging.exception("Failed to copy text")
            return {"ok": False, "error": str(exc)}

    def close(self) -> None:
        self.closed.set()
        with self.lock:
            runtime, self.runtime = self.runtime, None
        _request_server_stop(runtime)
        os._exit(0)


def _copy_text_to_macos(value: str) -> None:
    try:
        from AppKit import NSPasteboard
        from AppKit import NSPasteboardTypeString

        pasteboard = NSPasteboard.generalPasteboard()
        pasteboard.clearContents()
        if pasteboard.setString_forType_(value, NSPasteboardTypeString):
            return
        raise RuntimeError("macOS pasteboard rejected the text")
    except Exception:
        logging.debug("AppKit pasteboard copy failed; falling back to pbcopy", exc_info=True)

    subprocess.run(
        ["/usr/bin/pbcopy"],
        input=value,
        text=True,
        check=True,
        timeout=2,
    )


def _run_app() -> None:
    import webview

    runtime: ServerRuntime | None = None
    try:
        api = PortApi()
        api.window = webview.create_window(
            f"{APP_NAME} - Select Proxy Port",
            html=PORT_FORM_HTML,
            js_api=api,
            width=620,
            height=330,
        )
        api.window.events.closing += api.close
        webview.start()
    except Exception as exc:
        webview.create_window(
            APP_NAME,
            html=(
                "<h2>Xiaomi Mitmproxy 启动失败</h2>"
                f"<p>{exc}</p>"
                f"<p>日志：{_data_dir() / 'xiaomi-mitmproxy.log'}</p>"
            ),
            width=720,
            height=320,
        )
        webview.start()
    finally:
        if "api" in locals():
            api.stop()
        _stop_server(runtime)


def main() -> None:
    _run_app()


if __name__ == "__main__":
    main()
