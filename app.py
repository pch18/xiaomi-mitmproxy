"""Expose decrypted Xiaomi Cloud API bodies to the patched mitmweb UI."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from urllib.parse import parse_qs

from mitmproxy import http

from miutils import decrypt

API_DOMAINS = ("api.io.mi.com", "api.mijia.tech")
LOGIN_HOST = "account.xiaomi.com"
LOGIN_PATHS = ("/pass/serviceLogin", "/pass/serviceLoginAuth2")
LOGIN_SIDS = ("mijia", "xiaomiio")
DATA_DIR_ENV = "XIAOMI_MITMPROXY_DATA_DIR"
METADATA_KEY = "xiaomi_decoded"
COMMENT_HEADER = "[xiaomi decoded]"
logger = logging.getLogger(__name__)


def _data_file_path(filename: str) -> Path:
    if data_dir := os.environ.get(DATA_DIR_ENV):
        directory = Path(data_dir).expanduser()
        directory.mkdir(parents=True, exist_ok=True)
        return directory / filename
    return Path(__file__).resolve().parent / filename


def _ssecurity_path() -> Path:
    return _data_file_path("ssecurity.txt")


def _pass_token_path() -> Path:
    return _data_file_path("passToken.txt")


SSECURITY_PATH = _ssecurity_path()
PASS_TOKEN_PATH = _pass_token_path()


def _load_secret(path: Path) -> str:
    try:
        value = path.read_text().strip()
    except FileNotFoundError:
        path.touch(mode=0o600)
        value = ""
    path.chmod(0o600)
    return value


def _write_secret(path: Path, value: str) -> None:
    path.write_text(f"{value}\n")
    path.chmod(0o600)


def _load_ssecurity() -> str:
    return _load_secret(SSECURITY_PATH)


def _load_pass_token() -> str:
    return _load_secret(PASS_TOKEN_PATH)


SSECURITY = _load_ssecurity()
PASS_TOKEN = _load_pass_token()


def _matches_api_domain(host: str) -> bool:
    host = host.rstrip(".").lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in API_DOMAINS)


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
            raise ValueError("ssecurity.txt is empty; log in to Xiaomi or add ssecurity manually")
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
    flow.metadata[METADATA_KEY] = {
        "request": request_result,
        "response": response_result,
        "ssecurity": SSECURITY,
        "passToken": PASS_TOKEN,
    }
    flow.comment = _replace_generated_comment(flow.comment, COMMENT_HEADER)


def _login_sid(flow: http.HTTPFlow) -> str | None:
    values: list[str] = []
    values.extend(flow.request.query.get_all("sid"))
    if flow.request.method.upper() == "POST":
        content_type = flow.request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type.lower():
            values.extend(
                parse_qs(flow.request.get_text(strict=False), keep_blank_values=True).get("sid", [])
            )
    for value in values:
        sid = value.lower()
        if sid in LOGIN_SIDS:
            return sid
    return None


def _is_login_response(flow: http.HTTPFlow) -> bool:
    path = flow.request.path.split("?", 1)[0]
    return (
        flow.request.host.lower() == LOGIN_HOST
        and path in LOGIN_PATHS
        and _login_sid(flow) is not None
    )


def _login_response_json(text: str) -> object:
    start = text.find("{")
    if start < 0:
        raise ValueError("login response does not contain JSON")
    return json.loads(text[start:])


def _find_ssecurity(value: object) -> str | None:
    if isinstance(value, dict):
        candidate = value.get("ssecurity")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        for nested in value.values():
            if found := _find_ssecurity(nested):
                return found
    elif isinstance(value, list):
        for nested in value:
            if found := _find_ssecurity(nested):
                return found
    return None


def _find_login_credentials(value: object) -> tuple[str | None, str | None]:
    if isinstance(value, dict):
        candidate = value.get("ssecurity")
        if isinstance(candidate, str) and candidate.strip():
            pass_token = value.get("passToken")
            return candidate.strip(), pass_token.strip() if isinstance(pass_token, str) else None
        for nested in value.values():
            credentials = _find_login_credentials(nested)
            if credentials[0]:
                return credentials
    elif isinstance(value, list):
        for nested in value:
            credentials = _find_login_credentials(nested)
            if credentials[0]:
                return credentials
    return None, None


def _capture_ssecurity(flow: http.HTTPFlow) -> None:
    global PASS_TOKEN, SSECURITY

    assert flow.response is not None
    payload = _login_response_json(flow.response.get_text(strict=True))
    ssecurity, pass_token = _find_login_credentials(payload)
    if not ssecurity:
        raise ValueError("login response does not contain ssecurity")

    _write_secret(SSECURITY_PATH, ssecurity)
    SSECURITY = ssecurity
    if pass_token:
        _write_secret(PASS_TOKEN_PATH, pass_token)
        PASS_TOKEN = pass_token
    logger.info("Updated Xiaomi ssecurity in %s", SSECURITY_PATH)
    _broadcast_credentials()


def _broadcast_credentials() -> None:
    try:
        from mitmproxy.tools.web.app import ClientConnection

        ClientConnection.broadcast(
            type="state/update",
            payload={
                "xiaomiCredentials": {
                    "passToken": PASS_TOKEN,
                    "ssecurity": SSECURITY,
                }
            },
        )
    except Exception:
        logger.debug("Could not broadcast Xiaomi credentials", exc_info=True)


def request(flow: http.HTTPFlow) -> None:
    """Decode the request while keeping the original intercepted body intact."""
    if not _matches_api_domain(flow.request.host):
        return

    _update_decoded(flow, include_response=False)


def response(flow: http.HTTPFlow) -> None:
    """Decode the response and expose both plaintext bodies to mitmweb."""
    if flow.response is None:
        return

    if _is_login_response(flow):
        try:
            _capture_ssecurity(flow)
        except Exception as exc:
            logger.warning("Could not update Xiaomi ssecurity: %s", exc)

    if not _matches_api_domain(flow.request.host):
        return

    _update_decoded(flow, include_response=True)
