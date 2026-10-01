"""Tests for the shared TLS context (`netsuite._tls`) and that every
per-request httpx client is handed it, so the CA bundle is loaded once per
process rather than once per request."""

import ssl
from unittest.mock import patch

import certifi
import httpx
import pytest

from netsuite import _tls
from netsuite.oauth2 import _post_token
from netsuite.rest_api_base import RestApiBase


@pytest.fixture(autouse=True)
def _reset_shared_context():
    _tls._context = None
    yield
    _tls._context = None


class _ConcreteApi(RestApiBase):
    def __init__(self, config):
        self._config = config
        self._default_timeout = 10
        self._concurrent_requests = 5

    def _make_url(self, subpath):
        return f"https://example.com{subpath}"


def _capturing_client(captured, response):
    class _FakeClient:
        def __init__(self, **kw):
            captured.append(kw)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def request(self, **kw):
            return response

        async def post(self, *a, **kw):
            return response

    return _FakeClient


def test_shared_ssl_context_is_built_once():
    with patch.object(
        _tls, "_build_ssl_context", wraps=_tls._build_ssl_context
    ) as build:
        first = _tls.shared_ssl_context()
        second = _tls.shared_ssl_context()
    assert isinstance(first, ssl.SSLContext)
    assert first is second
    assert build.call_count == 1


def test_default_trust_store_is_certifi(monkeypatch):
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    with patch.object(_tls.ssl, "create_default_context") as create:
        _tls._build_ssl_context()
    create.assert_called_once_with(cafile=certifi.where())


def test_ssl_cert_file_env_overrides_certifi(monkeypatch, tmp_path):
    bundle = tmp_path / "ca.pem"
    bundle.write_text("")
    monkeypatch.setenv("SSL_CERT_FILE", str(bundle))
    with patch.object(_tls.ssl, "create_default_context") as create:
        _tls._build_ssl_context()
    create.assert_called_once_with(cafile=str(bundle))


def test_ssl_cert_dir_env_is_honoured(monkeypatch, tmp_path):
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.setenv("SSL_CERT_DIR", str(tmp_path))
    with patch.object(_tls.ssl, "create_default_context") as create:
        _tls._build_ssl_context()
    create.assert_called_once_with(capath=str(tmp_path))


def test_missing_env_paths_fall_back_to_certifi(monkeypatch, tmp_path):
    monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "nope.pem"))
    monkeypatch.setenv("SSL_CERT_DIR", str(tmp_path / "nope"))
    with patch.object(_tls.ssl, "create_default_context") as create:
        _tls._build_ssl_context()
    create.assert_called_once_with(cafile=certifi.where())


@pytest.mark.asyncio
async def test_request_impl_reuses_shared_context_across_requests(dummy_config):
    api = _ConcreteApi(dummy_config)
    captured: list = []
    response = httpx.Response(
        200, content=b"{}", request=httpx.Request("GET", "https://example.com/x")
    )
    with patch(
        "netsuite.rest_api_base.httpx.AsyncClient",
        _capturing_client(captured, response),
    ):
        await api._request_impl("GET", "/a")
        await api._request_impl("GET", "/b")

    assert len(captured) == 2
    assert captured[0]["verify"] is _tls.shared_ssl_context()
    assert captured[1]["verify"] is captured[0]["verify"]


@pytest.mark.asyncio
async def test_oauth2_token_fetch_uses_shared_context():
    captured: list = []
    response = httpx.Response(
        200,
        content=b'{"access_token": "t", "expires_in": 3600}',
        request=httpx.Request("POST", "https://example.com/token"),
    )
    with patch(
        "netsuite.oauth2.httpx.AsyncClient", _capturing_client(captured, response)
    ):
        await _post_token("https://example.com/token", {"grant_type": "x"})

    assert captured[0]["verify"] is _tls.shared_ssl_context()
