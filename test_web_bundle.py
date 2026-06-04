import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from mitmproxy import flowfilter
from mitmproxy.tools.web.app import State


DEFAULT_SEARCH_FILTER = "~d api.io.mi.com | ~d api.mijia.tech"
BUNDLE_PATH = Path("vendor/mitmproxy/tools/web/static/index-Be7e-cwP.js")
CSS_PATH = Path("vendor/mitmproxy/tools/web/static/xiaomi-comment.css")


class WebBundleSearchFilterTest(unittest.TestCase):
    def test_default_search_filter_is_valid(self) -> None:
        self.assertIsNotNone(flowfilter.parse(DEFAULT_SEARCH_FILTER))

    def test_bundle_applies_default_filter_on_initial_connection(self) -> None:
        bundle = BUNDLE_PATH.read_text()

        self.assertIn(f'search:"{DEFAULT_SEARCH_FILTER}",highlight:""', bundle)
        self.assertIn("this.filterState={},this.messageQueue=[]", bundle)
        self.assertNotIn('search:"mi.com",highlight:""', bundle)

    def test_bundle_exposes_current_credentials_in_footer(self) -> None:
        bundle = BUNDLE_PATH.read_text()

        self.assertIn("function XiaomiCurrentCredentials", bundle)
        self.assertIn("t.backendState.xiaomiCredentials?.passToken", bundle)
        self.assertIn("t.backendState.xiaomiCredentials?.ssecurity", bundle)
        self.assertIn('label:"passToken"', bundle)
        self.assertIn('label:"ssecurity"', bundle)
        self.assertIn("xiaomi-token-label", bundle)
        self.assertIn("label label-success xiaomi-token-label", bundle)

    def test_state_exposes_cached_credentials_on_startup(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "ssecurity.txt").write_text("cached-ssecurity\n")
            (data_dir / "passToken.txt").write_text("cached-pass-token\n")
            master = SimpleNamespace(proxyserver=SimpleNamespace(servers=[]))

            with patch.dict("os.environ", {"XIAOMI_MITMPROXY_DATA_DIR": str(data_dir)}):
                state = State.get_json(master)

        self.assertEqual(
            state["xiaomiCredentials"],
            {"passToken": "cached-pass-token", "ssecurity": "cached-ssecurity"},
        )

    def test_bundle_copy_uses_clipboard_and_non_alert_fallback(self) -> None:
        bundle = BUNDLE_PATH.read_text()

        self.assertIn("window.pywebview?.api?.copy_text", bundle)
        self.assertIn("await navigator.clipboard.writeText(e)", bundle)
        self.assertIn('new Blob([e],{type:"text/plain"})', bundle)
        self.assertIn("function XiaomiShowToast", bundle)
        self.assertIn("function XiaomiCopyString", bundle)
        self.assertIn("function XiaomiContentText", bundle)
        self.assertIn("const e=XiaomiCopyString(await t)", bundle)
        self.assertIn("Promise.resolve(XiaomiCopyString(t))", bundle)
        self.assertIn("o.jsx(Fa,{flow:s,message:i,content:_})", bundle)
        self.assertIn('await XiaomiCopyText(XiaomiContentText(t),"Copied")', bundle)
        self.assertIn('e="Copied"', bundle)
        self.assertIn('XiaomiShowToast("Copy failed")', bundle)
        self.assertNotIn("await Bl(h)", bundle)
        self.assertNotIn("const h=await p.json();await XiaomiCopyText", bundle)
        self.assertNotIn("alert(e)", bundle)
        self.assertNotIn('i&&"  copied"', bundle)

    def test_css_allows_body_text_selection(self) -> None:
        css = CSS_PATH.read_text()

        self.assertIn("section.xiaomi-decoded *", css)
        self.assertIn(".contentview", css)
        self.assertIn("-webkit-user-select: text", css)
        self.assertIn(".xiaomi-toast", css)


if __name__ == "__main__":
    unittest.main()
