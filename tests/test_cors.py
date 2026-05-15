"""Tests for hookbridge.cors — CORSConfig, _build_headers, CORSMiddleware."""

import pytest
from hookbridge.cors import CORSConfig, CORSMiddleware, _build_headers, _origin_allowed


# ---------------------------------------------------------------------------
# _origin_allowed
# ---------------------------------------------------------------------------

def test_wildcard_allows_any_origin():
    assert _origin_allowed("https://example.com", ["*"]) is True


def test_explicit_origin_allowed():
    assert _origin_allowed("https://example.com", ["https://example.com"]) is True


def test_unlisted_origin_denied():
    assert _origin_allowed("https://evil.com", ["https://example.com"]) is False


# ---------------------------------------------------------------------------
# _build_headers
# ---------------------------------------------------------------------------

def test_build_headers_returns_empty_for_disallowed_origin():
    cfg = CORSConfig(allow_origins=["https://good.com"])
    assert _build_headers(cfg, "https://bad.com") == []


def test_build_headers_contains_allow_origin():
    cfg = CORSConfig(allow_origins=["https://good.com"])
    headers = dict(_build_headers(cfg, "https://good.com"))
    assert headers["Access-Control-Allow-Origin"] == "https://good.com"


def test_build_headers_wildcard_uses_star():
    cfg = CORSConfig(allow_origins=["*"])
    headers = dict(_build_headers(cfg, "https://anything.com"))
    assert headers["Access-Control-Allow-Origin"] == "*"


def test_build_headers_includes_max_age():
    cfg = CORSConfig(max_age=300)
    headers = dict(_build_headers(cfg, "https://anything.com"))
    assert headers["Access-Control-Max-Age"] == "300"


def test_build_headers_omits_max_age_when_none():
    cfg = CORSConfig(max_age=None)
    headers = dict(_build_headers(cfg, "https://anything.com"))
    assert "Access-Control-Max-Age" not in headers


def test_build_headers_credentials():
    cfg = CORSConfig(allow_credentials=True)
    headers = dict(_build_headers(cfg, "https://anything.com"))
    assert headers["Access-Control-Allow-Credentials"] == "true"


def test_build_headers_expose_headers_present():
    cfg = CORSConfig(expose_headers=["X-Request-Id"])
    headers = dict(_build_headers(cfg, "https://anything.com"))
    assert headers["Access-Control-Expose-Headers"] == "X-Request-Id"


# ---------------------------------------------------------------------------
# CORSMiddleware
# ---------------------------------------------------------------------------

def _simple_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"hello"]


def _call(app, method="POST", origin="https://example.com", path="/hook"):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "HTTP_ORIGIN": origin,
    }
    captured = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = dict(headers)

    body = b"".join(app(environ, start_response))
    return captured["status"], captured["headers"], body


def test_middleware_adds_cors_header_to_normal_request():
    mw = CORSMiddleware(_simple_app)
    status, headers, _ = _call(mw)
    assert "Access-Control-Allow-Origin" in headers


def test_middleware_preflight_returns_204():
    mw = CORSMiddleware(_simple_app)
    status, headers, body = _call(mw, method="OPTIONS")
    assert status == "204 No Content"
    assert body == b""


def test_middleware_no_origin_passes_through_unchanged():
    mw = CORSMiddleware(_simple_app)
    environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/hook"}
    captured = {}

    def start_response(status, headers, exc_info=None):
        captured["headers"] = dict(headers)

    b"".join(mw(environ, start_response))
    assert "Access-Control-Allow-Origin" not in captured["headers"]


def test_middleware_disallowed_origin_no_cors_header():
    cfg = CORSConfig(allow_origins=["https://trusted.com"])
    mw = CORSMiddleware(_simple_app, config=cfg)
    status, headers, _ = _call(mw, origin="https://untrusted.com")
    assert "Access-Control-Allow-Origin" not in headers
