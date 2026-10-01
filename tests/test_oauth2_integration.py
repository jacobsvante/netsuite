"""Integration tests for OAuth 2.0: `Config` accepts the new auth types,
and `RestApiBase._make_auth` dispatches to the right httpx handler."""

import time
from unittest.mock import patch

import httpx
import pytest
from authlib.integrations.httpx_client import OAuth1Auth
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from netsuite import (
    Config,
    OAuth2AccessTokenAuth,
    OAuth2ClientCredentialsAuth,
    TokenAuth,
)
from netsuite.oauth2 import OAuth2BearerAuth
from netsuite.rest_api_base import RestApiBase


@pytest.fixture(scope="module")
def rsa_private_key_pem():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


class _ConcreteApi(RestApiBase):
    def __init__(self, config):
        self._config = config
        self._default_timeout = 10
        self._concurrent_requests = 5

    def _make_url(self, subpath):
        return f"https://example.com{subpath}"


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------


def test_config_accepts_oauth2_client_credentials(rsa_private_key_pem):
    config = Config(
        account="123456_SB1",
        auth=OAuth2ClientCredentialsAuth(
            client_id="my-app",
            certificate_id="cert-1",
            private_key_pem=rsa_private_key_pem,
        ),
    )
    assert config.is_oauth2_auth
    assert not config.is_token_auth


def test_config_accepts_oauth2_access_token():
    config = Config(
        account="123",
        auth=OAuth2AccessTokenAuth(access_token="prefetched"),
    )
    assert config.is_oauth2_auth


def test_config_token_auth_is_not_oauth2():
    config = Config(
        account="123",
        auth=TokenAuth(
            consumer_key="ck",
            consumer_secret="cs",
            token_id="ti",
            token_secret="ts",
        ),
    )
    assert config.is_token_auth
    assert not config.is_oauth2_auth


def test_oauth2_client_credentials_default_scope_and_alg():
    auth = OAuth2ClientCredentialsAuth(
        client_id="x",
        certificate_id="k",
        private_key_pem="pem",
    )
    assert auth.scope == ["rest_webservices"]
    assert auth.algorithm == "PS256"


# ---------------------------------------------------------------------------
# Auth dispatch
# ---------------------------------------------------------------------------


def test_make_auth_returns_oauth1_for_token_auth(dummy_config):
    api = _ConcreteApi(dummy_config)
    assert isinstance(api._make_auth(), OAuth1Auth)


def test_make_auth_returns_oauth2_bearer_for_client_credentials(
    rsa_private_key_pem,
):
    config = Config(
        account="123",
        auth=OAuth2ClientCredentialsAuth(
            client_id="my-app",
            certificate_id="cert",
            private_key_pem=rsa_private_key_pem,
            algorithm="RS256",
        ),
    )
    api = _ConcreteApi(config)
    auth = api._make_auth()
    assert isinstance(auth, OAuth2BearerAuth)


def test_make_auth_caches_oauth2_handler_across_calls(rsa_private_key_pem):
    """The handler holds the cached access token; we must not rebuild it
    on every request or we'd lose the cache."""
    config = Config(
        account="123",
        auth=OAuth2ClientCredentialsAuth(
            client_id="my-app",
            certificate_id="cert",
            private_key_pem=rsa_private_key_pem,
            algorithm="RS256",
        ),
    )
    api = _ConcreteApi(config)
    first = api._make_auth()
    second = api._make_auth()
    assert first is second


def test_make_auth_returns_oauth2_bearer_for_access_token_auth():
    config = Config(
        account="123",
        auth=OAuth2AccessTokenAuth(
            access_token="prefetched", expires_at=time.time() + 3600
        ),
    )
    api = _ConcreteApi(config)
    auth = api._make_auth()
    assert isinstance(auth, OAuth2BearerAuth)
    assert auth.token is not None
    assert auth.token.access_token == "prefetched"


@pytest.mark.asyncio
async def test_access_token_auth_does_not_refresh_automatically():
    """OAuth2AccessTokenAuth is bring-your-own-token. If the stored token
    expires we don't try to refresh — we raise a clear error so the caller
    knows to wire that into their upstream auth flow."""
    config = Config(
        account="123",
        auth=OAuth2AccessTokenAuth(
            access_token="stale",
            expires_at=time.time() - 1000,  # already expired
        ),
    )
    api = _ConcreteApi(config)
    auth = api._make_auth()
    request = httpx.Request("GET", "https://example.com/")
    with pytest.raises(RuntimeError, match="does not refresh automatically"):
        await auth.async_auth_flow(request).__anext__()


def test_make_auth_rejects_username_password_auth(dummy_username_password_config):
    """ODBC auth has no HTTP equivalent — make sure we don't silently
    fall through to a broken request."""
    api = _ConcreteApi(dummy_username_password_config)
    with pytest.raises(TypeError, match="Unsupported auth type"):
        api._make_auth()


# ---------------------------------------------------------------------------
# End-to-end: a request goes through with a Bearer header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_sends_bearer_header_for_client_credentials_auth(
    rsa_private_key_pem,
):
    """End-to-end: a request through `_request_impl` triggers the OAuth2
    handler, which mints a token via the token factory and stamps it on
    the outbound request as `Authorization: Bearer ...`."""
    from netsuite.oauth2 import OAuth2Token

    config = Config(
        account="123",
        auth=OAuth2ClientCredentialsAuth(
            client_id="my-app",
            certificate_id="cert",
            private_key_pem=rsa_private_key_pem,
            algorithm="RS256",
        ),
    )
    api = _ConcreteApi(config)
    captured_authorizations = []

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def request(self, **kw):
            # httpx normally runs the auth flow itself; we have to do it
            # by hand here since we've replaced AsyncClient entirely.
            auth_obj = kw["auth"]
            req = httpx.Request(kw["method"], kw["url"], headers=kw.get("headers"))
            async for prepared in auth_obj.async_auth_flow(req):
                captured_authorizations.append(prepared.headers.get("Authorization"))
            return httpx.Response(200, json={"ok": True}, request=req)

    # Bypass the real token endpoint by stubbing the exchange function:
    # it's the cleanest seam, and it lets us assert on the token that
    # ends up in the Authorization header.
    async def fake_exchange(*args, **kw):
        return OAuth2Token(access_token="live-token", expires_at=time.time() + 3600)

    with patch(
        "netsuite.rest_api_base.exchange_client_assertion", new=fake_exchange
    ), patch("netsuite.rest_api_base.httpx.AsyncClient", return_value=_FakeClient()):
        await api._request_impl("GET", "/x")

    assert captured_authorizations == ["Bearer live-token"]
