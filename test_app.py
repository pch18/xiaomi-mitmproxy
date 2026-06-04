import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import urlencode

from mitmproxy import connection, http

import app
from miutils import encrypt_rc4, get_signed_nonce

NONCE = "ttoNj0dlFDkBxMZ3"
TEST_SSECURITY = "dGVzdC1zc2VjdXJpdHk="
TEST_PASS_TOKEN = "dGVzdC1wYXNzLXRva2Vu"
SIGNED_NONCE = get_signed_nonce(TEST_SSECURITY, NONCE)


class XiaomiDecodedTabTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_ssecurity = app.SSECURITY
        self.original_ssecurity_path = app.SSECURITY_PATH
        self.original_pass_token = app.PASS_TOKEN
        self.original_pass_token_path = app.PASS_TOKEN_PATH
        self.temp_dir = TemporaryDirectory()
        app.SSECURITY = TEST_SSECURITY
        app.PASS_TOKEN = TEST_PASS_TOKEN
        app.SSECURITY_PATH = Path(self.temp_dir.name) / "ssecurity.txt"
        app.PASS_TOKEN_PATH = Path(self.temp_dir.name) / "passToken.txt"

    def tearDown(self) -> None:
        app.SSECURITY = self.original_ssecurity
        app.SSECURITY_PATH = self.original_ssecurity_path
        app.PASS_TOKEN = self.original_pass_token
        app.PASS_TOKEN_PATH = self.original_pass_token_path
        self.temp_dir.cleanup()

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
                "ssecurity": TEST_SSECURITY,
                "passToken": TEST_PASS_TOKEN,
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
                "ssecurity": TEST_SSECURITY,
                "passToken": TEST_PASS_TOKEN,
            },
        )

    def test_decodes_mijia_domain(self) -> None:
        flow = _flow(host="api.mijia.tech", request_plaintext="hello")
        app.request(flow)
        self.assertEqual(
            flow.metadata[app.METADATA_KEY],
            {
                "request": {"ok": True, "data": "hello"},
                "response": {"ok": False, "error": "Waiting for response.", "raw": ""},
                "ssecurity": TEST_SSECURITY,
                "passToken": TEST_PASS_TOKEN,
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

    def test_reports_empty_ssecurity_file_without_hiding_tabs(self) -> None:
        flow = _flow(host="api.io.mi.com", request_plaintext="hello")
        app.SSECURITY = ""
        app.request(flow)

        decoded = flow.metadata[app.METADATA_KEY]
        self.assertFalse(decoded["request"]["ok"])
        self.assertIn("ssecurity.txt", decoded["request"]["error"])
        self.assertEqual(decoded["response"]["error"], "Waiting for response.")
        self.assertEqual(decoded["ssecurity"], "")
        self.assertEqual(decoded["passToken"], TEST_PASS_TOKEN)

    def test_loads_ssecurity_from_file(self) -> None:
        app.SSECURITY_PATH.write_text(f"{TEST_SSECURITY}\n")
        self.assertEqual(app._load_ssecurity(), TEST_SSECURITY)

    def test_loads_pass_token_from_file(self) -> None:
        app.PASS_TOKEN_PATH.write_text(f"{TEST_PASS_TOKEN}\n")
        self.assertEqual(app._load_pass_token(), TEST_PASS_TOKEN)

    def test_creates_empty_ssecurity_file_when_missing(self) -> None:
        self.assertEqual(app._load_ssecurity(), "")
        self.assertTrue(app.SSECURITY_PATH.exists())
        self.assertEqual(app.SSECURITY_PATH.stat().st_mode & 0o777, 0o600)

    def test_uses_desktop_data_directory_when_configured(self) -> None:
        data_dir = Path(self.temp_dir.name) / "desktop-data"
        with patch.dict("os.environ", {app.DATA_DIR_ENV: str(data_dir)}):
            self.assertEqual(app._ssecurity_path(), data_dir / "ssecurity.txt")
            self.assertEqual(app._pass_token_path(), data_dir / "passToken.txt")
        self.assertTrue(data_dir.is_dir())

    def test_captures_ssecurity_and_pass_token_from_login_response(self) -> None:
        flow = _plain_flow(
            host="account.xiaomi.com",
            path="/pass/serviceLoginAuth2?sid=mijia",
            response='&&&START&&&{"code":0,"ssecurity":"bmV3LXNlY3VyaXR5","passToken":"bmV3LXBhc3MtdG9rZW4="}',
        )

        with patch("mitmproxy.tools.web.app.ClientConnection.broadcast") as broadcast:
            app.response(flow)

        self.assertEqual(app.SSECURITY, "bmV3LXNlY3VyaXR5")
        self.assertEqual(app.PASS_TOKEN, "bmV3LXBhc3MtdG9rZW4=")
        self.assertEqual(app.SSECURITY_PATH.read_text(), "bmV3LXNlY3VyaXR5\n")
        self.assertEqual(app.PASS_TOKEN_PATH.read_text(), "bmV3LXBhc3MtdG9rZW4=\n")
        broadcast.assert_called_once_with(
            type="state/update",
            payload={
                "xiaomiCredentials": {
                    "passToken": "bmV3LXBhc3MtdG9rZW4=",
                    "ssecurity": "bmV3LXNlY3VyaXR5",
                }
            },
        )

    def test_captures_ssecurity_from_service_login_get(self) -> None:
        flow = _plain_flow(
            host="account.xiaomi.com",
            method="GET",
            path="/pass/serviceLogin?sid=mijia&_json=true",
            response='&&&START&&&{"code":0,"ssecurity":"Z2V0LXNlY3VyaXR5"}',
        )

        app.response(flow)

        self.assertEqual(app.SSECURITY, "Z2V0LXNlY3VyaXR5")

    def test_captures_ssecurity_from_auth2_post_form_sid(self) -> None:
        flow = _plain_flow(
            host="account.xiaomi.com",
            method="POST",
            path="/pass/serviceLoginAuth2",
            content=urlencode({"_json": "true", "sid": "xiaomiio", "user": "17751619919"}),
            response='&&&START&&&{"code":0,"ssecurity":"cG9zdC1zZWN1cml0eQ=="}',
        )

        app.response(flow)

        self.assertEqual(app.SSECURITY, "cG9zdC1zZWN1cml0eQ==")

    def test_ignores_login_ssecurity_when_sid_is_not_supported(self) -> None:
        flow = _plain_flow(
            host="account.xiaomi.com",
            path="/pass/serviceLogin?sid=passport&_json=true",
            response='&&&START&&&{"code":0,"ssecurity":"aWdub3JlZA=="}',
        )

        app.response(flow)

        self.assertEqual(app.SSECURITY, TEST_SSECURITY)
        self.assertEqual(app.PASS_TOKEN, TEST_PASS_TOKEN)
        self.assertFalse(app.SSECURITY_PATH.exists())
        self.assertFalse(app.PASS_TOKEN_PATH.exists())

    def test_captures_nested_ssecurity_from_login_response(self) -> None:
        flow = _plain_flow(
            host="account.xiaomi.com",
            path="/pass/serviceLoginAuth2?sid=xiaomiio",
            response='{"data":{"ssecurity":"bmVzdGVkLXNlY3VyaXR5"}}',
        )

        app.response(flow)

        self.assertEqual(app.SSECURITY, "bmVzdGVkLXNlY3VyaXR5")


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


def _plain_flow(
    *,
    host: str,
    path: str,
    response: str,
    method: str = "POST",
    content: str | None = None,
) -> http.HTTPFlow:
    client = connection.Client(peername=("127.0.0.1", 12345), sockname=("127.0.0.1", 8080))
    server = connection.Server(address=(host, 443))
    flow = http.HTTPFlow(client, server)
    headers = {}
    if content is not None:
        headers["content-type"] = "application/x-www-form-urlencoded"
    flow.request = http.Request.make(
        method,
        f"https://{host}{path}",
        content=content or b"",
        headers=headers,
    )
    flow.response = http.Response.make(200, response)
    return flow


if __name__ == "__main__":
    unittest.main()
