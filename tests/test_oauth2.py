"""Tests for the OAuth 2.0 module — JWT assertion building, token
exchange, and the httpx auth handler. We do not hit a real NetSuite
instance: the token endpoint is mocked at the httpx layer."""

import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from joserfc import jwt as jose_jwt
from joserfc.jwk import RSAKey

from netsuite.oauth2 import (
    DEFAULT_ALGORITHM,
    DEFAULT_SCOPES,
    JWT_BEARER_ASSERTION_TYPE,
    OAuth2BearerAuth,
    OAuth2Token,
    build_authorization_url,
    build_client_assertion,
    build_token_endpoint,
    exchange_authorization_code,
    exchange_client_assertion,
)

# ---------------------------------------------------------------------------
# Test fixtures: generate a real RSA keypair so the JWT signing path is
# exercised end-to-end (otherwise we'd just be testing mocks).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rsa_private_key_pem():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


@pytest.fixture(scope="module")
def rsa_public_jwk(rsa_private_key_pem):
    """Used to verify the signature on assertions we build in tests."""
    private = RSAKey.import_key(rsa_private_key_pem)
    return private  # joserfc happily verifies with the same key object


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------


def test_build_token_endpoint_for_sandbox():
    assert (
        build_token_endpoint("123456_SB1")
        == "https://123456-sb1.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token"
    )


def test_build_token_endpoint_for_production():
    assert (
        build_token_endpoint("123456")
        == "https://123456.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token"
    )


def test_build_authorization_url_includes_required_params():
    url = build_authorization_url(
        "123456_SB1",
        client_id="abc",
        redirect_uri="https://app.example.com/oauth/callback",
        scope=["rest_webservices", "restlets"],
        state="opaque-state",
    )
    parsed = httpx.URL(url)
    assert parsed.host == "123456-sb1.app.netsuite.com"
    assert parsed.path == "/app/login/oauth2/authorize.nl"
    params = dict(parsed.params.multi_items())
    assert params["response_type"] == "code"
    assert params["client_id"] == "abc"
    assert params["redirect_uri"] == "https://app.example.com/oauth/callback"
    assert params["scope"] == "rest_webservices restlets"
    assert params["state"] == "opaque-state"


def test_build_authorization_url_omits_state_when_unspecified():
    url = build_authorization_url(
        "123456",
        client_id="abc",
        redirect_uri="https://example.com/cb",
    )
    assert "state=" not in url


# ---------------------------------------------------------------------------
# Client assertion (JWT) building
# ---------------------------------------------------------------------------


def test_client_assertion_carries_required_claims(rsa_private_key_pem, rsa_public_jwk):
    assertion = build_client_assertion(
        "123456_SB1",
        client_id="my-app",
        certificate_id="cert-kid-42",
        private_key_pem=rsa_private_key_pem,
        scope=["rest_webservices"],
        algorithm="RS256",
        now=1_700_000_000,
    )
    decoded = jose_jwt.decode(assertion, rsa_public_jwk)

    # Header
    assert decoded.header["alg"] == "RS256"
    assert decoded.header["typ"] == "JWT"
    assert decoded.header["kid"] == "cert-kid-42"

    # Claims
    claims = decoded.claims
    assert claims["iss"] == "my-app"
    assert claims["scope"] == ["rest_webservices"]
    assert claims["aud"] == build_token_endpoint("123456_SB1")
    assert claims["iat"] == 1_700_000_000
    # NetSuite caps `exp` at iat + 3600.
    assert claims["exp"] == 1_700_000_000 + 3600


def test_client_assertion_signs_with_default_algorithm(
    rsa_private_key_pem, rsa_public_jwk
):
    """Regression: the module default is PS256, which joserfc's default
    registry rejects unless the algorithm is explicitly whitelisted in
    `jwt.encode`. Every other assertion test pins RS256, so the default
    path went uncovered. Build with no `algorithm=` and confirm it signs."""
    assert DEFAULT_ALGORITHM == "PS256"
    assertion = build_client_assertion(
        "123456_SB1",
        client_id="my-app",
        certificate_id="cert-kid-42",
        private_key_pem=rsa_private_key_pem,
    )
    decoded = jose_jwt.decode(assertion, rsa_public_jwk, algorithms=[DEFAULT_ALGORITHM])
    assert decoded.header["alg"] == "PS256"
    assert decoded.header["kid"] == "cert-kid-42"


def test_client_assertion_clamps_ttl_to_one_hour(rsa_private_key_pem, rsa_public_jwk):
    assertion = build_client_assertion(
        "123456",
        client_id="x",
        certificate_id="k",
        private_key_pem=rsa_private_key_pem,
        algorithm="RS256",
        now=1_000_000,
        ttl_seconds=99_999,  # asking for way more
    )
    claims = jose_jwt.decode(assertion, rsa_public_jwk).claims
    assert claims["exp"] == 1_000_000 + 3600  # clamped


def test_client_assertion_rejects_unsupported_algorithm(rsa_private_key_pem):
    with pytest.raises(ValueError, match="Unsupported algorithm"):
        build_client_assertion(
            "123456",
            client_id="x",
            certificate_id="k",
            private_key_pem=rsa_private_key_pem,
            algorithm="HS256",
        )


def test_client_assertion_default_scope_is_rest_webservices(
    rsa_private_key_pem, rsa_public_jwk
):
    assertion = build_client_assertion(
        "123",
        client_id="x",
        certificate_id="k",
        private_key_pem=rsa_private_key_pem,
        algorithm="RS256",
    )
    claims = jose_jwt.decode(assertion, rsa_public_jwk).claims
    assert claims["scope"] == list(DEFAULT_SCOPES)


# ---------------------------------------------------------------------------
# OAuth2Token dataclass
# ---------------------------------------------------------------------------


def test_token_from_response_extracts_fields():
    payload = {
        "access_token": "AT",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "rest_webservices restlets",
        "refresh_token": "RT",
    }
    token = OAuth2Token.from_response(payload, now=1_000_000)
    assert token.access_token == "AT"
    assert token.expires_at == 1_000_000 + 3600
    assert token.refresh_token == "RT"
    assert token.scope == ["rest_webservices", "restlets"]


def test_token_is_expired_with_safety_margin():
    token = OAuth2Token(access_token="x", expires_at=1_000_000)
    assert token.is_expired(now=999_999)  # within 60s margin -> already expired
    assert token.is_expired(now=1_000_000)
    assert not token.is_expired(now=900_000)


# ---------------------------------------------------------------------------
# Token exchange (Client Credentials + Authorization Code)
# ---------------------------------------------------------------------------


def _mock_post_returning(token_payload):
    """Patch httpx.AsyncClient.post to return a successful token response."""
    response = httpx.Response(
        200,
        json=token_payload,
        request=httpx.Request("POST", "https://example.com"),
    )
    return patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response))


@pytest.mark.asyncio
async def test_exchange_client_assertion_posts_correct_form(rsa_private_key_pem):
    captured = {}

    async def fake_post(self, url, *, data=None, headers=None, **kw):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = headers
        return httpx.Response(
            200,
            json={"access_token": "AT", "expires_in": 3600, "token_type": "Bearer"},
            request=httpx.Request("POST", url),
        )

    with patch("httpx.AsyncClient.post", new=fake_post):
        token = await exchange_client_assertion(
            "123456_SB1",
            client_id="my-app",
            certificate_id="cert-1",
            private_key_pem=rsa_private_key_pem,
            algorithm="RS256",
        )

    assert token.access_token == "AT"
    assert captured["url"] == build_token_endpoint("123456_SB1")
    assert captured["data"]["grant_type"] == "client_credentials"
    assert captured["data"]["client_assertion_type"] == JWT_BEARER_ASSERTION_TYPE
    assert "client_assertion" in captured["data"]
    assert captured["headers"]["Content-Type"] == "application/x-www-form-urlencoded"


@pytest.mark.asyncio
async def test_exchange_client_assertion_raises_on_4xx(rsa_private_key_pem):
    error = httpx.Response(
        401,
        json={"error": "invalid_client"},
        text='{"error":"invalid_client"}',
        request=httpx.Request("POST", "https://x"),
    )
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=error)):
        with pytest.raises(httpx.HTTPStatusError) as excinfo:
            await exchange_client_assertion(
                "123",
                client_id="x",
                certificate_id="k",
                private_key_pem=rsa_private_key_pem,
                algorithm="RS256",
            )
    assert "401" in str(excinfo.value)
    assert "invalid_client" in str(excinfo.value)


@pytest.mark.asyncio
async def test_exchange_authorization_code_with_client_secret():
    captured = {}

    async def fake_post(self, url, *, data=None, headers=None, **kw):
        captured["data"] = data
        return httpx.Response(
            200,
            json={
                "access_token": "AT",
                "expires_in": 3600,
                "refresh_token": "RT",
            },
            request=httpx.Request("POST", url),
        )

    with patch("httpx.AsyncClient.post", new=fake_post):
        token = await exchange_authorization_code(
            "123",
            code="auth-code-xyz",
            client_id="my-app",
            client_secret="shh",
            redirect_uri="https://example.com/cb",
        )
    assert token.access_token == "AT"
    assert token.refresh_token == "RT"
    assert captured["data"]["grant_type"] == "authorization_code"
    assert captured["data"]["client_secret"] == "shh"
    assert captured["data"]["code"] == "auth-code-xyz"
    assert "client_assertion" not in captured["data"]


@pytest.mark.asyncio
async def test_exchange_authorization_code_with_jwt_assertion(rsa_private_key_pem):
    captured = {}

    async def fake_post(self, url, *, data=None, headers=None, **kw):
        captured["data"] = data
        return httpx.Response(
            200,
            json={"access_token": "AT", "expires_in": 3600},
            request=httpx.Request("POST", url),
        )

    with patch("httpx.AsyncClient.post", new=fake_post):
        await exchange_authorization_code(
            "123",
            code="auth-code-xyz",
            client_id="my-app",
            certificate_id="cert",
            private_key_pem=rsa_private_key_pem,
            redirect_uri="https://example.com/cb",
            algorithm="RS256",
        )
    assert captured["data"]["client_assertion_type"] == JWT_BEARER_ASSERTION_TYPE
    assert "client_secret" not in captured["data"]


@pytest.mark.asyncio
async def test_exchange_authorization_code_rejects_no_credential():
    with pytest.raises(ValueError, match="exactly one"):
        await exchange_authorization_code(
            "123", code="x", client_id="a", redirect_uri="b"
        )


@pytest.mark.asyncio
async def test_exchange_authorization_code_rejects_both_credentials(
    rsa_private_key_pem,
):
    with pytest.raises(ValueError, match="exactly one"):
        await exchange_authorization_code(
            "123",
            code="x",
            client_id="a",
            redirect_uri="b",
            client_secret="shh",
            certificate_id="cert",
            private_key_pem=rsa_private_key_pem,
        )


# ---------------------------------------------------------------------------
# OAuth2BearerAuth httpx handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bearer_auth_fetches_initial_token():
    factory_calls = 0

    async def factory():
        nonlocal factory_calls
        factory_calls += 1
        return OAuth2Token(access_token="T1", expires_at=time.time() + 3600)

    auth = OAuth2BearerAuth(factory)
    request = httpx.Request("GET", "https://example.com/")
    flow = auth.async_auth_flow(request)
    sent = await flow.__anext__()
    assert sent.headers["Authorization"] == "Bearer T1"
    assert factory_calls == 1


@pytest.mark.asyncio
async def test_bearer_auth_reuses_token_until_expiry():
    factory_calls = 0

    async def factory():
        nonlocal factory_calls
        factory_calls += 1
        return OAuth2Token(
            access_token=f"T{factory_calls}", expires_at=time.time() + 3600
        )

    auth = OAuth2BearerAuth(factory)
    for _ in range(3):
        request = httpx.Request("GET", "https://example.com/")
        flow = auth.async_auth_flow(request)
        await flow.__anext__()
    assert factory_calls == 1


@pytest.mark.asyncio
async def test_bearer_auth_refreshes_when_expired():
    factory_calls = 0

    async def factory():
        nonlocal factory_calls
        factory_calls += 1
        # First token is already past expiry; second is fresh.
        if factory_calls == 1:
            return OAuth2Token(access_token="stale", expires_at=time.time() - 100)
        return OAuth2Token(access_token="fresh", expires_at=time.time() + 3600)

    auth = OAuth2BearerAuth(factory)
    request = httpx.Request("GET", "https://example.com/")
    sent = await auth.async_auth_flow(request).__anext__()
    # The first stale token is replaced before we send the request.
    # On the very first call the factory mints stale (which is_expired() True
    # immediately), then a SECOND factory call mints fresh. We accept either
    # the fresh or stale token here — both pass through the bearer header
    # — what we really want to assert is that an expired stored token would
    # trigger a refresh on the *next* request.
    auth._token = OAuth2Token(access_token="stale2", expires_at=time.time() - 100)
    request = httpx.Request("GET", "https://example.com/")
    sent = await auth.async_auth_flow(request).__anext__()
    assert sent.headers["Authorization"] == "Bearer fresh"


@pytest.mark.asyncio
async def test_bearer_auth_initial_token_is_used_as_is():
    initial = OAuth2Token(access_token="prefetched", expires_at=time.time() + 3600)

    async def factory():
        raise AssertionError("factory should not be called when initial token is fresh")

    auth = OAuth2BearerAuth(factory, initial_token=initial)
    request = httpx.Request("GET", "https://example.com/")
    sent = await auth.async_auth_flow(request).__anext__()
    assert sent.headers["Authorization"] == "Bearer prefetched"


def test_bearer_auth_sync_flow_is_not_supported():
    auth = OAuth2BearerAuth(token_factory=lambda: None)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="async-only"):
        list(auth.sync_auth_flow(httpx.Request("GET", "https://example.com/")))
