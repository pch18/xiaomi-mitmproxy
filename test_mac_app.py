import unittest
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import mac_app


class MacAppPortTest(unittest.TestCase):
    def test_finds_available_random_web_port(self) -> None:
        sock = MagicMock()
        sock.__enter__.return_value = sock
        sock.getsockname.return_value = (mac_app.WEB_HOST, 49152)
        with patch("socket.socket", return_value=sock):
            self.assertEqual(mac_app._find_free_web_port(), 49152)
        sock.bind.assert_called_once_with((mac_app.WEB_HOST, 0))

    def test_detects_occupied_port(self) -> None:
        with patch("socket.create_connection"):
            self.assertFalse(mac_app._port_is_available(mac_app.WEB_HOST, 8080))

    def test_detects_available_port_by_failed_connection(self) -> None:
        with patch("socket.create_connection", side_effect=OSError("connection refused")):
            self.assertTrue(mac_app._port_is_available("0.0.0.0", 8080))

    def test_reads_lan_address_from_default_route_interface(self) -> None:
        route = MagicMock(stdout="   interface: en0\n")
        ipconfig = MagicMock(stdout="10.0.0.167\n")
        with patch("subprocess.run", side_effect=[route, ipconfig]):
            self.assertEqual(mac_app._lan_address(), "10.0.0.167")

    def test_window_title_contains_proxy_address(self) -> None:
        with patch.object(mac_app, "_lan_address", return_value="10.0.0.167"):
            self.assertEqual(
                mac_app._window_title(8088),
                "Xiaomi Mitmproxy  [ Proxy Address = 10.0.0.167:8088 ]",
            )

    def test_app_always_opens_port_form_with_default_port(self) -> None:
        class EventHook:
            def __init__(self) -> None:
                self.callbacks = []

            def __iadd__(self, callback):
                self.callbacks.append(callback)
                return self

        window = MagicMock()
        closing = EventHook()
        window.events.closing = closing
        webview = SimpleNamespace(
            create_window=MagicMock(return_value=window),
            start=MagicMock(),
        )

        with patch.dict(sys.modules, {"webview": webview}):
            mac_app._run_app()

        _, kwargs = webview.create_window.call_args
        self.assertIn('value="8080"', kwargs["html"])
        self.assertIsInstance(kwargs["js_api"], mac_app.PortApi)
        self.assertEqual(closing.callbacks, [kwargs["js_api"].close])
        webview.start.assert_called_once_with()

    def test_port_api_resizes_window_before_loading_main_page(self) -> None:
        runtime = mac_app.ServerRuntime(proxy_port=8082, web_port=49152)
        window = MagicMock()
        window.x = 380
        window.y = 340
        window.width = 620
        window.height = 330
        api = mac_app.PortApi()
        api.window = window

        with (
            patch.object(mac_app, "_port_is_available", return_value=True),
            patch.object(mac_app, "_start_server", return_value=runtime),
            patch.object(mac_app, "_wait_until_ready"),
            patch.object(mac_app, "_lan_address", return_value="10.0.0.167"),
        ):
            self.assertEqual(api.start("8082"), {"ok": True})

        window.move.assert_called_once_with(178, 205)
        window.resize.assert_called_once_with(
            mac_app.MAIN_WINDOW_WIDTH,
            mac_app.MAIN_WINDOW_HEIGHT,
        )
        self.assertEqual(
            window.title,
            "Xiaomi Mitmproxy  [ Proxy Address = 10.0.0.167:8082 ]",
        )
        window.load_url.assert_called_once_with(runtime.web_url)

    def test_port_api_stop_releases_running_server(self) -> None:
        runtime = mac_app.ServerRuntime(proxy_port=8080, web_port=49152)
        api = mac_app.PortApi()
        api.runtime = runtime

        with patch.object(mac_app, "_stop_server") as stop_server:
            api.stop()

        self.assertTrue(api.closed.is_set())
        self.assertIsNone(api.runtime)
        stop_server.assert_called_once_with(runtime)

    def test_port_api_stops_server_if_window_closes_during_startup(self) -> None:
        runtime = mac_app.ServerRuntime(proxy_port=8080, web_port=49152)
        api = mac_app.PortApi()
        api.window = MagicMock()
        api.closed.set()

        with (
            patch.object(mac_app, "_port_is_available", return_value=True),
            patch.object(mac_app, "_start_server", return_value=runtime),
            patch.object(mac_app, "_wait_until_ready"),
            patch.object(mac_app, "_stop_server") as stop_server,
        ):
            result = api.start("8080")

        self.assertEqual(result, {"ok": False, "error": "应用窗口已关闭。"})
        self.assertIsNone(api.runtime)
        stop_server.assert_called_once_with(runtime)

    def test_port_api_close_stops_server_and_exits_process(self) -> None:
        runtime = mac_app.ServerRuntime(proxy_port=8080, web_port=49152)
        api = mac_app.PortApi()
        api.runtime = runtime

        with (
            patch.object(mac_app, "_request_server_stop") as request_stop,
            patch.object(mac_app.os, "_exit") as exit_process,
        ):
            api.close()

        self.assertTrue(api.closed.is_set())
        self.assertIsNone(api.runtime)
        request_stop.assert_called_once_with(runtime)
        exit_process.assert_called_once_with(0)

    def test_port_api_copy_text_uses_native_clipboard(self) -> None:
        api = mac_app.PortApi()
        pasteboard = SimpleNamespace(
            clearContents=MagicMock(),
            setString_forType_=MagicMock(return_value=True),
        )
        appkit = SimpleNamespace(
            NSPasteboard=SimpleNamespace(generalPasteboard=MagicMock(return_value=pasteboard)),
            NSPasteboardTypeString="public.utf8-plain-text",
        )

        with patch.dict(sys.modules, {"AppKit": appkit}):
            self.assertEqual(api.copy_text("hello"), {"ok": True})

        pasteboard.clearContents.assert_called_once_with()
        pasteboard.setString_forType_.assert_called_once_with("hello", "public.utf8-plain-text")

    def test_port_api_copy_text_coerces_values_to_strings(self) -> None:
        api = mac_app.PortApi()
        pasteboard = SimpleNamespace(
            clearContents=MagicMock(),
            setString_forType_=MagicMock(return_value=True),
        )
        appkit = SimpleNamespace(
            NSPasteboard=SimpleNamespace(generalPasteboard=MagicMock(return_value=pasteboard)),
            NSPasteboardTypeString="public.utf8-plain-text",
        )

        with patch.dict(sys.modules, {"AppKit": appkit}):
            self.assertEqual(api.copy_text({"text": "hello"}), {"ok": True})

        pasteboard.setString_forType_.assert_called_once_with(
            "{'text': 'hello'}",
            "public.utf8-plain-text",
        )

    def test_port_api_copy_text_falls_back_to_pbcopy(self) -> None:
        api = mac_app.PortApi()
        pasteboard = SimpleNamespace(
            clearContents=MagicMock(),
            setString_forType_=MagicMock(return_value=False),
        )
        appkit = SimpleNamespace(
            NSPasteboard=SimpleNamespace(generalPasteboard=MagicMock(return_value=pasteboard)),
            NSPasteboardTypeString="public.utf8-plain-text",
        )

        with (
            patch.dict(sys.modules, {"AppKit": appkit}),
            patch("subprocess.run") as run,
        ):
            self.assertEqual(api.copy_text("hello"), {"ok": True})

        run.assert_called_once_with(
            ["/usr/bin/pbcopy"],
            input="hello",
            text=True,
            check=True,
            timeout=2,
        )


if __name__ == "__main__":
    unittest.main()
