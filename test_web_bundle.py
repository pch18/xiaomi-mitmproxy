import unittest
from pathlib import Path

from mitmproxy import flowfilter


DEFAULT_SEARCH_FILTER = "~d api.io.mi.com | ~d api.mijia.tech"
BUNDLE_PATH = Path("vendor/mitmproxy/tools/web/static/index-Be7e-cwP.js")


class WebBundleSearchFilterTest(unittest.TestCase):
    def test_default_search_filter_is_valid(self) -> None:
        self.assertIsNotNone(flowfilter.parse(DEFAULT_SEARCH_FILTER))

    def test_bundle_applies_default_filter_on_initial_connection(self) -> None:
        bundle = BUNDLE_PATH.read_text()

        self.assertIn(f'search:"{DEFAULT_SEARCH_FILTER}",highlight:""', bundle)
        self.assertIn("this.filterState={},this.messageQueue=[]", bundle)
        self.assertNotIn('search:"mi.com",highlight:""', bundle)


if __name__ == "__main__":
    unittest.main()
