import asyncio
import functools
import logging
import random
import time
from functools import cached_property

import httpx
from authlib.integrations.httpx_client import OAuth1Auth
from authlib.oauth1.rfc5849.client_auth import ClientAuth
from authlib.oauth1.rfc5849.signature import generate_signature_base_string
from oauthlib.oauth1.rfc5849.signature import sign_hmac_sha256

from . import json
from ._tls import shared_ssl_context
from .config import (
    OAuth2AccessTokenAuth,
    OAuth2ClientCredentialsAuth,
    TokenAuth,
)
from .exceptions import NetsuiteAPIRequestError, NetsuiteAPIResponseParsingError
from .oauth2 import (
    OAuth2BearerAuth,
    OAuth2Token,
    exchange_client_assertion,
)

__all__ = ("RestApiBase",)

DEFAULT_SIGNATURE_METHOD = "HMAC-SHA256"

# NetSuite answers HTTP 429 when the account's concurrent-request limit is
# exhausted (`CONCURRENCY_LIMIT_EXCEEDED`). The request was rejected, not
# executed, so re-sending it is safe for writes as well as reads.
DEFAULT_MAX_RETRIES_ON_429 = 5
_RETRY_BACKOFF_BASE_SECONDS = 1.0
_RETRY_BACKOFF_MAX_SECONDS = 30.0

logger = logging.getLogger(__name__)


def authlib_hmac_sha256_sign_method(client, request):
    """Sign a HMAC-SHA256 signature."""
    base_string = generate_signature_base_string(request)
    return sign_hmac_sha256(base_string, client.client_secret, client.token_secret)


ClientAuth.register_signature_method("HMAC-SHA256", authlib_hmac_sha256_sign_method)


class RestApiBase:
    _concurrent_requests: int = 10
    _default_timeout: int = 10
    _signature_method: str = DEFAULT_SIGNATURE_METHOD
    _max_retries_on_429: int = DEFAULT_MAX_RETRIES_ON_429

    @cached_property
    def _request_semaphore(self) -> asyncio.Semaphore:
        # NOTE: Shouldn't be put in __init__ as we might not have a running
        #       event loop at that time.
        return asyncio.Semaphore(self._concurrent_requests)

    async def _request(self, method: str, subpath: str, **request_kw):
        resp = await self._request_impl(method, subpath, **request_kw)

        if resp.status_code < 200 or resp.status_code > 299:
            raise NetsuiteAPIRequestError(resp.status_code, resp.text)

        if resp.status_code == 204:
            return None
        else:
            try:
                return json.loads(resp.text)
            except Exception:
                raise NetsuiteAPIResponseParsingError(resp.status_code, resp.text)

    async def _request_impl(
        self, method: str, subpath: str, **request_kw
    ) -> httpx.Response:
        method = method.upper()
        url = request_kw.pop("url", self._make_url(subpath))

        headers = {**self._make_default_headers(), **request_kw.pop("headers", {})}

        timeout = request_kw.pop("timeout", self._default_timeout)

        if "json" in request_kw:
            request_kw["data"] = json.dumps(request_kw.pop("json"))

        kw = {**request_kw}
        logger.debug(
            f"Making {method.upper()} request to {url}. Keyword arguments: {kw}"
        )

        attempt = 0
        while True:
            async with self._request_semaphore:
                async with httpx.AsyncClient(verify=shared_ssl_context()) as c:
                    resp = await c.request(
                        method=method,
                        url=url,
                        headers=headers,
                        auth=self._make_auth(),
                        timeout=timeout,
                        **kw,
                    )
            if resp.status_code != 429 or attempt >= self._max_retries_on_429:
                break
            attempt += 1
            delay = self._retry_delay(resp, attempt)
            logger.warning(
                f"NetSuite returned HTTP 429 for {method} {url}; "
                f"retry {attempt}/{self._max_retries_on_429} in {delay:.1f}s"
            )
            # Sleep outside the semaphore so a backing-off request doesn't
            # hold a concurrency slot.
            await asyncio.sleep(delay)

        resp_headers_json = json.dumps(dict(resp.headers))
        logger.debug(f"Got response headers from NetSuite: {resp_headers_json}")

        return resp

    @staticmethod
    def _retry_delay(resp: httpx.Response, attempt: int) -> float:
        """Seconds to wait before retry number `attempt` (1-based).

        Honours a numeric `Retry-After` header; otherwise exponential
        backoff with jitter so concurrent callers don't retry in lockstep.
        """
        retry_after = resp.headers.get("Retry-After", "")
        try:
            return min(max(float(retry_after), 0.0), _RETRY_BACKOFF_MAX_SECONDS)
        except ValueError:
            pass
        backoff = _RETRY_BACKOFF_BASE_SECONDS * 2 ** (attempt - 1)
        jitter = random.uniform(0, _RETRY_BACKOFF_BASE_SECONDS)
        return min(backoff + jitter, _RETRY_BACKOFF_MAX_SECONDS)

    def _make_url(self, subpath: str):
        raise NotImplementedError

    def _make_auth(self):
        auth = self._config.auth
        if isinstance(auth, TokenAuth):
            return OAuth1Auth(
                client_id=auth.consumer_key,
                client_secret=auth.consumer_secret,
                token=auth.token_id,
                token_secret=auth.token_secret,
                realm=self._config.account,
                force_include_body=True,
                signature_method=self._signature_method,
            )
        if isinstance(auth, OAuth2ClientCredentialsAuth):
            # The auth handler caches the token across calls; we lazily
            # bind a `token_factory` that knows how to mint a fresh one.
            token_factory = functools.partial(
                exchange_client_assertion,
                self._config.account,
                client_id=auth.client_id,
                certificate_id=auth.certificate_id,
                private_key_pem=auth.private_key_pem,
                scope=auth.scope,
                algorithm=auth.algorithm,
            )
            cached = getattr(self, "_oauth2_handler", None)
            if cached is None:
                cached = OAuth2BearerAuth(token_factory)
                # Cache on the instance so token re-use works across
                # back-to-back requests.
                self._oauth2_handler = cached  # type: ignore[attr-defined]
            return cached
        if isinstance(auth, OAuth2AccessTokenAuth):
            # Bring-your-own token. We don't refresh; the user wired
            # that in upstream. We still wrap it in OAuth2BearerAuth so
            # the Authorization header is set consistently.
            initial = OAuth2Token(
                access_token=auth.access_token,
                expires_at=auth.expires_at or (time.time() + 3600),
                refresh_token=auth.refresh_token,
            )

            async def _no_refresh() -> OAuth2Token:
                raise RuntimeError(
                    "OAuth2AccessTokenAuth does not refresh automatically. "
                    "Provide a fresh token via your own auth flow."
                )

            return OAuth2BearerAuth(_no_refresh, initial_token=initial)
        raise TypeError(
            f"Unsupported auth type for HTTP requests: {type(auth).__name__}. "
            f"Use TokenAuth, OAuth2ClientCredentialsAuth, or "
            f"OAuth2AccessTokenAuth."
        )

    def _make_default_headers(self):
        return {"Content-Type": "application/json"}
