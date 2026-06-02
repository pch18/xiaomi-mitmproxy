import unittest
import os
from urllib.parse import urlencode

from mitmproxy import connection, http

os.environ["XIAOMI_SSECURITY"] = "dGVzdC1zc2VjdXJpdHk="

import app
from miutils import encrypt_rc4, get_signed_nonce

NONCE = "ttoNj0dlFDkBxMZ3"
SIGNED_NONCE = get_signed_nonce(app.SSECURITY, NONCE)


class XiaomiDecodedTabTest(unittest.TestCase):
    def test_stores_plaintext_without_modifying_original_bodies(self) -> None:
        flow = _flow(
            host="api.io.mi.com",
            request_plaintext='{"request":true}',
            response_plaintext='{"response":true}',
        )
        original_request = flow.request.content
        original_response = flow.response.content

        app.request(flow)
        app.response(flow)

        self.assertEqual(
            flow.metadata[app.METADATA_KEY],
            {
                "request": {"ok": True, "data": {"request": True}},
                "response": {"ok": True, "data": {"response": True}},
            },
        )
        self.assertEqual(flow.request.content, original_request)
        self.assertEqual(flow.response.content, original_response)
        self.assertEqual(flow.comment, "[xiaomi decoded]")

    def test_decodes_subdomain(self) -> None:
        flow = _flow(host="de.api.io.mi.com", request_plaintext="hello")
        app.request(flow)
        self.assertEqual(
            flow.metadata[app.METADATA_KEY],
            {
                "request": {"ok": True, "data": "hello"},
                "response": {"ok": False, "error": "Waiting for response.", "raw": ""},
            },
        )

    def test_ignores_unrelated_domain(self) -> None:
        flow = _flow(host="example.com", request_plaintext="hello", response_plaintext="world")
        app.request(flow)
        app.response(flow)
        self.assertNotIn(app.METADATA_KEY, flow.metadata)
        self.assertEqual(flow.comment, "")

    def test_reports_missing_form_fields_without_interrupting_flow(self) -> None:
        flow = _flow(host="api.io.mi.com", request_plaintext="hello")
        flow.request.content = b"foo=bar"
        app.request(flow)
        self.assertIn(app.METADATA_KEY, flow.metadata)
        self.assertFalse(flow.metadata[app.METADATA_KEY]["request"]["ok"])
        self.assertEqual(flow.metadata[app.METADATA_KEY]["request"]["raw"], "foo=bar")
        self.assertEqual(flow.comment, "[xiaomi decoded]")

    def test_reports_response_decode_failure_and_preserves_raw_body(self) -> None:
        flow = _flow(host="api.io.mi.com", request_plaintext="hello")
        flow.response = http.Response.make(200, "not encrypted")

        app.request(flow)
        app.response(flow)

        result = flow.metadata[app.METADATA_KEY]["response"]
        self.assertFalse(result["ok"])
        self.assertEqual(result["raw"], "not encrypted")

    def test_reports_missing_ssecurity_without_hiding_tabs(self) -> None:
        flow = _flow(host="api.io.mi.com", request_plaintext="hello")
        original_ssecurity = app.SSECURITY
        app.SSECURITY = ""
        try:
            app.request(flow)
        finally:
            app.SSECURITY = original_ssecurity

        decoded = flow.metadata[app.METADATA_KEY]
        self.assertFalse(decoded["request"]["ok"])
        self.assertIn("XIAOMI_SSECURITY", decoded["request"]["error"])
        self.assertEqual(decoded["response"]["error"], "Waiting for response.")


def _flow(
    *,
    host: str,
    request_plaintext: str,
    response_plaintext: str | None = None,
) -> http.HTTPFlow:
    client = connection.Client(peername=("127.0.0.1", 12345), sockname=("127.0.0.1", 8080))
    server = connection.Server(address=(host, 443))
    flow = http.HTTPFlow(client, server)
    request_form = urlencode(
        {
            "_nonce": NONCE,
            "data": encrypt_rc4(SIGNED_NONCE, request_plaintext),
        }
    )
    flow.request = http.Request.make(
        "POST",
        f"https://{host}/api",
        content=request_form,
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    if response_plaintext is not None:
        flow.response = http.Response.make(200, encrypt_rc4(SIGNED_NONCE, response_plaintext))
    return flow


if __name__ == "__main__":
    unittest.main()
