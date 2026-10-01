"""OAuth 2.0 support for NetSuite.

NetSuite is gradually removing SOAP Web Services (2025.2 is the last
planned SOAP endpoint, with older endpoints losing support over the
following releases). The recommended path forward is the REST API
authenticated via OAuth 2.0.
This module implements the two flows that matter for a backend library:

* **Client Credentials with JWT Bearer Assertion** (RFC 7523 — *machine-
  to-machine*). The integration uploads a public key/cert to NetSuite,
  signs a short-lived JWT with the matching private key, and exchanges
  it for an access token at NetSuite's token endpoint. No browser, no
  user interaction. This is what most server-to-server integrations
  should use.

* **Authorization Code Grant** — interactive. We provide the helper
  functions to build the authorization URL and exchange the resulting
  authorization code for tokens, but the redirect dance itself is left
  to the calling application (a Flask/FastAPI app, a CLI tool, etc.) —
  the library has no opinion on how you serve the redirect URI.

For both flows the resulting access token is plugged into a single
``OAuth2BearerAuth`` httpx auth handler that the REST API and Restlet
clients use transparently in place of the legacy OAuth 1.0a token-based
auth.

Reference: NetSuite OAuth 2.0 documentation, "Issue Token and Revoke
Token REST Services" and "OAuth 2.0 for Integration Application
Authentication".
"""

import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Iterable, List, Optional

import httpx
from joserfc import jwt
from joserfc.jwk import ECKey, RSAKey

from . import json as nsjson
from ._tls import shared_ssl_context

__all__ = (
    "DEFAULT_SCOPES",
    "JWT_BEARER_ASSERTION_TYPE",
    "OAuth2BearerAuth",
    "OAuth2Token",
    "build_authorization_url",
    "build_client_assertion",
    "build_token_endpoint",
    "exchange_authorization_code",
    "exchange_client_assertion",
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JWT_BEARER_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
DEFAULT_SCOPES: tuple = ("rest_webservices",)
# The NetSuite-recommended algorithm for the client assertion. PS256 is
# RSA-PSS w/ SHA-256; ES256 is ECDSA on P-256 w/ SHA-256. Both are
# accepted by the token endpoint.
SUPPORTED_ALGORITHMS: tuple = ("PS256", "RS256", "ES256", "ES384", "ES512")
DEFAULT_ALGORITHM = "PS256"

# How long before expiry we treat a token as already expired and refresh.
# NetSuite's access tokens last ~1 hour; 60 s of slack is plenty.
_EXPIRY_SAFETY_MARGIN_SECONDS = 60


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------


def _account_slug(account: str) -> str:
    """Replicates `Config.account_slugified` without importing it (which
    would create a circular dependency for callers that pass a string)."""
    return account.lower().replace("_", "-")


def build_token_endpoint(account: str) -> str:
    """The OAuth 2.0 token endpoint for a given NetSuite account."""
    return (
        f"https://{_account_slug(account)}"
        ".suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token"
    )


def build_authorization_url(
    account: str,
    *,
    client_id: str,
    redirect_uri: str,
    scope: Iterable[str] = DEFAULT_SCOPES,
    state: Optional[str] = None,
) -> str:
    """Build the URL the user should be redirected to in their browser
    to start the Authorization Code Grant flow.

    The calling app is responsible for serving ``redirect_uri`` and
    extracting the ``code`` query parameter, which is then handed to
    :func:`exchange_authorization_code`.
    """
    base = (
        f"https://{_account_slug(account)}"
        ".app.netsuite.com/app/login/oauth2/authorize.nl"
    )
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scope),
    }
    if state is not None:
        params["state"] = state
    return str(httpx.URL(base).copy_with(params=params))


# ---------------------------------------------------------------------------
# JWT client assertion
# ---------------------------------------------------------------------------


def _load_signing_key(private_key_pem: str, algorithm: str):
    """Load a PEM-encoded private key into the right joserfc JWK type for
    the chosen algorithm. RS*/PS* algorithms need RSA; ES* need EC."""
    family = algorithm[:2].upper()
    if family in ("RS", "PS"):
        return RSAKey.import_key(private_key_pem)
    if family == "ES":
        return ECKey.import_key(private_key_pem)
    raise ValueError(
        f"Unsupported algorithm '{algorithm}'. "
        f"Expected one of {SUPPORTED_ALGORITHMS}."
    )


def build_client_assertion(
    account: str,
    *,
    client_id: str,
    certificate_id: str,
    private_key_pem: str,
    scope: Iterable[str] = DEFAULT_SCOPES,
    algorithm: str = DEFAULT_ALGORITHM,
    now: Optional[int] = None,
    ttl_seconds: int = 3600,
) -> str:
    """Build and sign a JWT to use as the ``client_assertion`` in a
    Client Credentials token request.

    ``certificate_id`` is the ``kid`` NetSuite assigns when you upload
    the matching public key/certificate. ``private_key_pem`` is the
    matching private key in PEM format.

    NetSuite caps assertion ``exp`` at one hour; ``ttl_seconds`` is
    clamped to that ceiling.
    """
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"Unsupported algorithm '{algorithm}'. "
            f"Expected one of {SUPPORTED_ALGORITHMS}."
        )
    issued_at = int(now if now is not None else time.time())
    expires_at = issued_at + min(ttl_seconds, 3600)
    header = {"alg": algorithm, "typ": "JWT", "kid": certificate_id}
    claims = {
        "iss": client_id,
        "scope": list(scope),
        "aud": build_token_endpoint(account),
        "iat": issued_at,
        "exp": expires_at,
    }
    key = _load_signing_key(private_key_pem, algorithm)
    # joserfc's default registry only permits its "recommended" algorithms
    # (RS256/ES256/...), and rejects PS256 — which is this module's default,
    # and NetSuite's recommended assertion algorithm. Explicitly whitelist the
    # chosen algorithm so every entry in SUPPORTED_ALGORITHMS actually signs.
    return jwt.encode(header, claims, key, algorithms=[algorithm])


# ---------------------------------------------------------------------------
# Token exchanges
# ---------------------------------------------------------------------------


@dataclass
class OAuth2Token:
    """The result of any successful token exchange.

    NetSuite returns ``access_token`` plus ``expires_in`` (seconds) for
    Client Credentials, and adds ``refresh_token`` for Authorization
    Code Grant. ``expires_at`` is computed locally so callers can decide
    whether to refresh.
    """

    access_token: str
    token_type: str = "Bearer"
    expires_at: float = 0.0
    refresh_token: Optional[str] = None
    scope: List[str] = field(default_factory=list)

    @classmethod
    def from_response(
        cls, payload: dict, *, now: Optional[float] = None
    ) -> "OAuth2Token":
        issued = now if now is not None else time.time()
        scope = payload.get("scope", "")
        if isinstance(scope, str):
            scope = scope.split()
        return cls(
            access_token=payload["access_token"],
            token_type=payload.get("token_type", "Bearer"),
            expires_at=issued + float(payload.get("expires_in", 0)),
            refresh_token=payload.get("refresh_token"),
            scope=list(scope),
        )

    def is_expired(self, *, now: Optional[float] = None) -> bool:
        when = now if now is not None else time.time()
        return when >= (self.expires_at - _EXPIRY_SAFETY_MARGIN_SECONDS)


async def _post_token(
    url: str,
    data: dict,
    *,
    timeout: float = 30.0,
) -> OAuth2Token:
    async with httpx.AsyncClient(
        timeout=timeout, verify=shared_ssl_context()
    ) as client:
        resp = await client.post(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code >= 400:
        # Surface the server-side error message rather than just the status.
        raise httpx.HTTPStatusError(
            f"NetSuite token endpoint returned {resp.status_code}: {resp.text}",
            request=resp.request,
            response=resp,
        )
    return OAuth2Token.from_response(nsjson.loads(resp.text))


async def exchange_client_assertion(
    account: str,
    *,
    client_id: str,
    certificate_id: str,
    private_key_pem: str,
    scope: Iterable[str] = DEFAULT_SCOPES,
    algorithm: str = DEFAULT_ALGORITHM,
) -> OAuth2Token:
    """Run the Client Credentials + JWT Bearer flow end-to-end and
    return a fresh access token."""
    assertion = build_client_assertion(
        account,
        client_id=client_id,
        certificate_id=certificate_id,
        private_key_pem=private_key_pem,
        scope=scope,
        algorithm=algorithm,
    )
    return await _post_token(
        build_token_endpoint(account),
        {
            "grant_type": "client_credentials",
            "client_assertion_type": JWT_BEARER_ASSERTION_TYPE,
            "client_assertion": assertion,
        },
    )


async def exchange_authorization_code(
    account: str,
    *,
    code: str,
    client_id: str,
    redirect_uri: str,
    client_secret: Optional[str] = None,
    certificate_id: Optional[str] = None,
    private_key_pem: Optional[str] = None,
    algorithm: str = DEFAULT_ALGORITHM,
) -> OAuth2Token:
    """Exchange an authorization code for an access + refresh token.

    NetSuite supports two ways to authenticate the code-exchange request:
    a shared ``client_secret`` (basic auth) or the same JWT bearer
    assertion used by Client Credentials. Pass whichever your integration
    is configured for. Exactly one must be provided.
    """
    has_secret = client_secret is not None
    has_assertion = certificate_id is not None and private_key_pem is not None
    if has_secret == has_assertion:
        raise ValueError(
            "Provide exactly one of `client_secret` or "
            "(`certificate_id` + `private_key_pem`) for the code exchange."
        )

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    if has_secret:
        data["client_id"] = client_id
        data["client_secret"] = client_secret  # type: ignore[assignment]
    else:
        assertion = build_client_assertion(
            account,
            client_id=client_id,
            certificate_id=certificate_id,  # type: ignore[arg-type]
            private_key_pem=private_key_pem,  # type: ignore[arg-type]
            algorithm=algorithm,
        )
        data["client_assertion_type"] = JWT_BEARER_ASSERTION_TYPE
        data["client_assertion"] = assertion

    return await _post_token(build_token_endpoint(account), data)


# ---------------------------------------------------------------------------
# httpx.Auth subclass
# ---------------------------------------------------------------------------


class OAuth2BearerAuth(httpx.Auth):
    """An httpx auth handler that sets ``Authorization: Bearer <token>``.

    When the token is missing or close to expiry, ``token_factory`` is
    awaited to mint a fresh one. Callers compose the factory: e.g. for
    Client Credentials, partial-apply :func:`exchange_client_assertion`;
    for a bring-your-own token, return a static ``OAuth2Token``.

    The class is async-first because the rest of this library is. We
    don't expose a sync flow — there isn't one anywhere else either.
    """

    requires_response_body = False

    def __init__(
        self,
        token_factory: Callable[[], Awaitable[OAuth2Token]],
        *,
        initial_token: Optional[OAuth2Token] = None,
    ) -> None:
        self._token_factory = token_factory
        self._token: Optional[OAuth2Token] = initial_token

    @property
    def token(self) -> Optional[OAuth2Token]:
        """The currently cached token, if any. Mostly useful in tests."""
        return self._token

    def sync_auth_flow(self, request):  # pragma: no cover - not supported
        raise RuntimeError(
            "OAuth2BearerAuth is async-only. Use httpx.AsyncClient "
            "(which the rest of this library does)."
        )

    async def async_auth_flow(self, request):
        if self._token is None or self._token.is_expired():
            self._token = await self._token_factory()
        request.headers["Authorization"] = f"Bearer {self._token.access_token}"
        yield request
