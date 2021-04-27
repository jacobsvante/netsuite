import asyncio
import logging

from . import json
from .exceptions import NetsuiteAPIRequestError, NetsuiteAPIResponseParsingError
from .util import cached_property

try:
    import httpx
except ImportError:

    class httpx:  # type: ignore[no-redef]
        Response = None


try:
    from authlib.integrations.httpx_client import OAuth1Auth
except ImportError:
    OAuth1Auth = None

__all__ = ("RestApiBase",)

logger = logging.getLogger(__name__)


class RestApiBase:
    _concurrent_requests: int = 10
    _default_timeout: int = 10

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
        url = self._make_url(subpath)

        headers = {**self._make_default_headers(), **request_kw.pop("headers", {})}

        timeout = request_kw.pop("timeout", self._default_timeout)

        if "json" in request_kw:
            request_kw["data"] = json.dumps(request_kw.pop("json"))

        kw = {**request_kw}
        logger.debug(
            f"Making {method.upper()} request to {url}. Keyword arguments: {kw}"
        )

        async with self._request_semaphore:
            async with httpx.AsyncClient() as c:
                resp = await c.request(
                    method=method,
                    url=url,
                    headers=headers,
                    auth=self._make_auth(),
                    timeout=timeout,
                    **kw,
                )

        resp_headers_json = json.dumps(dict(resp.headers))
        logger.debug(f"Got response headers from NetSuite: {resp_headers_json}")

        return resp

    def _make_url(self, subpath: str):
        raise NotImplementedError

    def _make_auth(self):
        auth = self._config.auth
        return OAuth1Auth(
            client_id=auth.consumer_key,
            client_secret=auth.consumer_secret,
            token=auth.token_id,
            token_secret=auth.token_secret,
            realm=self._config.account,
            force_include_body=True,
        )

    def _make_default_headers(self):
        return {"Content-Type": "application/json"}
