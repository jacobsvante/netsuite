import asyncio
import logging
from typing import Iterable, Optional

from . import json
from .types import JsonDict

try:
    import httpx
except ImportError:

    class httpx:
        Response = None  # NOTE: For type hint to work


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
        default_timeout: str = 60,
        concurrent_requests: int = 10,
    ):
        if not self.has_required_dependencies():
            raise RuntimeError(
                "Missing required dependencies for REST API support. "
                "Install with `pip install netsuite[rest_api]`"
            )
        self._account = account
        self._hostname = self._make_hostname()
        self._auth = self._make_auth(
            account, consumer_key, consumer_secret, token_id, token_secret
        )
        self._default_timeout = default_timeout
        self._request_semaphore = asyncio.Semaphore(concurrent_requests)

    @classmethod
    def has_required_dependencies(cls) -> bool:
        return httpx is not None and OAuth1Auth is not None

    async def get(self, subpath: str, **request_kw) -> JsonDict:
        return await self.request("GET", subpath, **request_kw)

    async def post(self, subpath: str, **request_kw):
        return await self.request("POST", subpath, **request_kw,)

    async def put(self, subpath: str, **request_kw):
        return await self.request("PUT", subpath, **request_kw)

    async def patch(self, subpath: str, **request_kw):
        return await self.request("PATCH", subpath, **request_kw)

    async def delete(self, subpath: str, **request_kw):
        return await self.request("DELETE", subpath, **request_kw)

    async def suiteql(self, q: str, limit: int = 10, offset: int = 0) -> JsonDict:
        return await self.request(
            "POST",
            "/query/v1/suiteql",
            headers={"Prefer": "transient"},
            json={"q": q},
            params={"limit": limit, "offset": offset},
        )

    async def jsonschema(self, record_type: str, **request_kw) -> JsonDict:
        headers = {
            **request_kw.pop("headers", {}),
            "Accept": "application/schema+json",
        }
        return await self.request(
            "GET",
            f"/record/v1/metadata-catalog/{record_type}",
            headers=headers,
            **request_kw,
        )

    async def openapi(self, record_types: Iterable[str] = (), **request_kw) -> JsonDict:
        headers = {
            **request_kw.pop("headers", {}),
            "Accept": "application/swagger+json",
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

    async def request(
        self, method: str, subpath: str, **request_kw
    ) -> Optional[JsonDict]:
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

        auth = request_kw.pop("auth", self._auth)
        timeout = request_kw.pop("timeout", self._default_timeout)

        if "json" in request_kw:
            request_kw["data"] = json.dumps_str(request_kw.pop("json"))

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
                    auth=auth,
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

    @staticmethod
    def _make_auth(
        account: str,
        consumer_key: str,
        consumer_secret: str,
        token_id: str,
        token_secret: str,
    ):
        return OAuth1Auth(
            client_id=consumer_key,
            client_secret=consumer_secret,
            token=token_id,
            token_secret=token_secret,
            realm=account,
        )

    def _make_default_headers(self):
        return {
            "Content-Type": "application/json",
            "X-NetSuite-PropertyNameValidation": "error",
        }
