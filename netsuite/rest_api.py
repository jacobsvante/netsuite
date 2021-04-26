import asyncio
import logging
from typing import Sequence

from . import json
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


logger = logging.getLogger(__name__)

__all__ = ("NetSuiteRestApi",)


class NetsuiteAPIRequestError(Exception):
    """Raised when a Netsuite REST API request fails"""

    def __init__(self, status_code: int, response_text: str):
        self.status_code = status_code
        self.response_text = response_text

    def __str__(self):
        return f"HTTP{self.status_code} - {self.response_text}"


class NetsuiteAPIResponseParsingError(NetsuiteAPIRequestError):
    """Raised when parsing a Netsuite REST API response fails"""


class NetSuiteRestApi:
    def __init__(
        self,
        *,
        account: str,
        consumer_key: str,
        consumer_secret: str,
        token_id: str,
        token_secret: str,
        default_timeout: int = 60,
        concurrent_requests: int = 10,
    ):
        if not self.has_required_dependencies():
            raise RuntimeError(
                "Missing required dependencies for REST API support. "
                "Install with `pip install netsuite[rest_api]`"
            )
        self._account = account
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._token_id = token_id
        self._token_secret = token_secret
        self._hostname = self._make_hostname()
        self._default_timeout = default_timeout
        self._concurrent_requests = concurrent_requests

    @cached_property
    def request_semaphore(self) -> asyncio.Semaphore:
        # NOTE: Shouldn't be put in __init__ as we might not have a running
        #       event loop at that time.
        return asyncio.Semaphore(self._concurrent_requests)

    @classmethod
    def has_required_dependencies(cls) -> bool:
        return httpx is not None and OAuth1Auth is not None

    async def get(self, subpath: str, **request_kw):
        return await self.request("GET", subpath, **request_kw)

    async def post(self, subpath: str, **request_kw):
        return await self.request(
            "POST",
            subpath,
            **request_kw,
        )

    async def put(self, subpath: str, **request_kw):
        return await self.request("PUT", subpath, **request_kw)

    async def patch(self, subpath: str, **request_kw):
        return await self.request("PATCH", subpath, **request_kw)

    async def delete(self, subpath: str, **request_kw):
        return await self.request("DELETE", subpath, **request_kw)

    async def suiteql(self, q: str, limit: int = 10, offset: int = 0, **request_kw):
        return await self.request(
            "POST",
            "/query/v1/suiteql",
            headers={"Prefer": "transient", **request_kw.pop("headers", {})},
            json={"q": q, **request_kw.pop("json", {})},
            params={"limit": limit, "offset": offset, **request_kw.pop("params", {})},
            **request_kw,
        )

    async def jsonschema(self, record_type: str, **request_kw):
        headers = {
            "Accept": "application/schema+json",
            **request_kw.pop("headers", {}),
        }
        return await self.request(
            "GET",
            f"/record/v1/metadata-catalog/{record_type}",
            headers=headers,
            **request_kw,
        )

    async def openapi(self, record_types: Sequence[str] = (), **request_kw):
        headers = {
            "Accept": "application/swagger+json",
            **request_kw.pop("headers", {}),
        }
        params = request_kw.pop("params", {})

        if len(record_types) > 0:
            params["select"] = ",".join(record_types)

        return await self.request(
            "GET",
            "/record/v1/metadata-catalog",
            headers=headers,
            params=params,
            **request_kw,
        )

    async def request(self, method: str, subpath: str, **request_kw):
        resp = await self._raw_request(method, subpath, **request_kw)

        if resp.status_code < 200 or resp.status_code > 299:
            raise NetsuiteAPIRequestError(resp.status_code, resp.text)

        if resp.status_code == 204:
            return None
        else:
            try:
                return json.loads(resp.text)
            except Exception:
                raise NetsuiteAPIResponseParsingError(resp.status_code, resp.text)

    async def _raw_request(
        self, method: str, subpath: str, **request_kw
    ) -> httpx.Response:
        method = method.upper()
        url = self._make_url(subpath)
        headers = {**self._make_default_headers(), **request_kw.pop("headers", {})}

        timeout = request_kw.pop("timeout", self._default_timeout)

        if "json" in request_kw:
            request_kw["data"] = json.dumps_str(request_kw.pop("json"))

        kw = {**request_kw}
        logger.debug(
            f"Making {method.upper()} request to {url}. Keyword arguments: {kw}"
        )

        async with self.request_semaphore:
            async with httpx.AsyncClient() as c:
                resp = await c.request(
                    method=method,
                    url=url,
                    headers=headers,
                    auth=self._make_auth(),
                    timeout=timeout,
                    **kw,
                )

        resp_headers_json = json.dumps_str(dict(resp.headers))
        logger.debug(
            f"Got response headers from NetSuite REST API: {resp_headers_json}"
        )

        return resp

    def _make_hostname(self):
        account_slugified = self._account.lower().replace("_", "-")
        return f"{account_slugified}.suitetalk.api.netsuite.com"

    def _make_url(self, subpath: str):
        return f"https://{self._hostname}/services/rest{subpath}"

    def _make_auth(self):
        return OAuth1Auth(
            client_id=self._consumer_key,
            client_secret=self._consumer_secret,
            token=self._token_id,
            token_secret=self._token_secret,
            realm=self._account,
            force_include_body=True,
        )

    def _make_default_headers(self):
        return {
            "Content-Type": "application/json",
            "X-NetSuite-PropertyNameValidation": "error",
        }
