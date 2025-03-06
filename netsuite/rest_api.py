import logging
from functools import cached_property
from typing import Sequence

from . import rest_api_base
from .config import Config

logger = logging.getLogger(__name__)

__all__ = ("NetSuiteRestApi",)


class NetSuiteRestApi(rest_api_base.RestApiBase):
    def __init__(
        self,
        config: Config,
        *,
        default_timeout: int = 60,
        concurrent_requests: int = 10,
        signature_method: str = rest_api_base.DEFAULT_SIGNATURE_METHOD,
    ):
        self._config = config
        self._default_timeout = default_timeout
        self._concurrent_requests = concurrent_requests
        self._signature_method = signature_method

    @cached_property
    def hostname(self) -> str:
        return self._make_hostname()

    async def request(self, method: str, subpath: str, **request_kw):
        return await self._request_impl(method, subpath, **request_kw)

    async def get(self, subpath: str, **request_kw):
        return await self._request("GET", subpath, **request_kw)

    async def post(self, subpath: str, **request_kw):
        return await self._request(
            "POST",
            subpath,
            **request_kw,
        )

    async def put(self, subpath: str, **request_kw):
        return await self._request("PUT", subpath, **request_kw)

    async def patch(self, subpath: str, **request_kw):
        return await self._request("PATCH", subpath, **request_kw)

    async def delete(self, subpath: str, **request_kw):
        return await self._request("DELETE", subpath, **request_kw)

    # TODO maybe break out params vs poping?
    async def suiteql(self, q: str, limit: int = 10, offset: int = 0, **request_kw):
        """
        Example:
        >>> suiteql(q="SELECT * FROM Transaction", limit=10, offset=0)

        Documentation:

        - https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_156257799794.html#Using-SuiteQL
        """
        return await self._request(
            "POST",
            "/query/v1/suiteql",
            headers={"Prefer": "transient", **request_kw.pop("headers", {})},
            json={"q": q, **request_kw.pop("json", {})},
            # limit & offset look like the only available params
            params={"limit": limit, "offset": offset, **request_kw.pop("params", {})},
            **request_kw,
        )

    async def jsonschema(self, record_type: str, **request_kw):
        headers = {
            "Accept": "application/schema+json",
            **request_kw.pop("headers", {}),
        }
        return await self._request(
            "GET",
            f"/record/v1/metadata-catalog/{record_type}",
            headers=headers,
            **request_kw,
        )

    async def token_info(self, **request_kw):
        """
        Retrieves metadata about the current token. Role, company, etc.

        https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/chapter_157017286140.html#Issue-Token-and-Revoke-Token-REST-Services-for-Token-based-Authentication
        """

        # this overrides the default URL generation: this specific endpoint hits a completely different host
        request_kw["url"] = (
            f"https://{self._config.account_slugified}.restlets.api.netsuite.com/rest/tokeninfo"
        )

        return await self._request(
            method="GET",
            # useless, but required by _request
            subpath="ignored",
            **request_kw,
        )

    async def openapi(self, record_types: Sequence[str] = (), **request_kw):
        """
        Retrieves the OpenAPI specification (metadata catalog) for the Netsuite REST API. This is the best way to
        introspect the NetSuite account and return the record structure.

        https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_1545126526.html

        Args:
            record_types (Sequence[str]): Optional. List of record types to include in the OpenAPI specification.
            **request_kw: Optional keyword arguments to be passed to the underlying request.

        Returns:
            The OpenAPI specification as a JSON object.
        """

        headers = {
            "Accept": "application/swagger+json",
            **request_kw.pop("headers", {}),
        }
        params = request_kw.pop("params", {})

        if len(record_types) > 0:
            params["select"] = ",".join(record_types)

        return await self._request(
            "GET",
            "/record/v1/metadata-catalog",
            headers=headers,
            params=params,
            **request_kw,
        )

    def _make_hostname(self):
        return f"{self._config.account_slugified}.suitetalk.api.netsuite.com"

    def _make_url(self, subpath: str):
        return f"https://{self.hostname}/services/rest{subpath}"

    def _make_default_headers(self):
        return {
            "Content-Type": "application/json",
            "X-NetSuite-PropertyNameValidation": "error",
        }
