"""Expose decrypted Xiaomi Cloud API bodies to the patched mitmweb UI."""

from __future__ import annotations

import json
import os
from urllib.parse import parse_qs

from mitmproxy import http

from miutils import decrypt

API_DOMAIN = "api.io.mi.com"
SSECURITY = os.environ.get("XIAOMI_SSECURITY", "")
METADATA_KEY = "xiaomi_decoded"
COMMENT_HEADER = "[xiaomi decoded]"


def _matches_api_domain(host: str) -> bool:
    host = host.rstrip(".").lower()
    return host == API_DOMAIN or host.endswith(f".{API_DOMAIN}")


def _json_value(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _request_fields(flow: http.HTTPFlow) -> tuple[str, str]:
    content_type = flow.request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" not in content_type.lower():
        raise ValueError(f"unexpected request content-type: {content_type or '<missing>'}")

    form = parse_qs(flow.request.get_text(strict=True), keep_blank_values=True)
    nonce = form.get("_nonce", [None])[0]
    encrypted_data = form.get("data", [None])[0]
    if not nonce or not encrypted_data:
        raise ValueError("request form must contain _nonce and data")
    return nonce, encrypted_data


def _result(*, raw: str, value: object | None = None, error: Exception | None = None) -> dict[str, object]:
    if error is not None:
        return {"ok": False, "error": f"{type(error).__name__}: {error}", "raw": raw}
    return {"ok": True, "data": value}


def _waiting_response() -> dict[str, object]:
    return {"ok": False, "error": "Waiting for response.", "raw": ""}


def _request_result(flow: http.HTTPFlow) -> tuple[str | None, dict[str, object]]:
    raw = flow.request.get_text(strict=False)
    try:
        if not SSECURITY:
            raise ValueError("XIAOMI_SSECURITY environment variable is not configured")
        nonce, encrypted_request = _request_fields(flow)
        return nonce, _result(raw=raw, value=_json_value(decrypt(SSECURITY, nonce, encrypted_request)))
    except Exception as exc:
        return None, _result(raw=raw, error=exc)


def _response_result(flow: http.HTTPFlow, nonce: str | None) -> dict[str, object]:
    if flow.response is None:
        return _waiting_response()

    raw = flow.response.get_text(strict=False)
    try:
        if nonce is None:
            raise ValueError("cannot decrypt response because request nonce is unavailable")
        encrypted_response = flow.response.get_text(strict=True).strip()
        if not encrypted_response:
            raise ValueError("response body is empty")
        return _result(raw=raw, value=_json_value(decrypt(SSECURITY, nonce, encrypted_response)))
    except Exception as exc:
        return _result(raw=raw, error=exc)


def _replace_generated_comment(existing: str, generated: str) -> str:
    manual_comment = existing.split(COMMENT_HEADER, 1)[0].rstrip()
    return f"{manual_comment}\n\n{generated}" if manual_comment else generated


def _update_decoded(flow: http.HTTPFlow, include_response: bool) -> None:
    nonce, request_result = _request_result(flow)
    response_result = _response_result(flow, nonce) if include_response else _waiting_response()
    flow.metadata[METADATA_KEY] = {"request": request_result, "response": response_result}
    flow.comment = _replace_generated_comment(flow.comment, COMMENT_HEADER)


def request(flow: http.HTTPFlow) -> None:
    """Decode the request while keeping the original intercepted body intact."""
    if not _matches_api_domain(flow.request.host):
        return

    _update_decoded(flow, include_response=False)


def response(flow: http.HTTPFlow) -> None:
    """Decode the response and expose both plaintext bodies to mitmweb."""
    if flow.response is None or not _matches_api_domain(flow.request.host):
        return

    _update_decoded(flow, include_response=True)
