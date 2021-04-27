import logging

from .config import Config
from .rest_api_base import RestApiBase
from .util import cached_property

logger = logging.getLogger(__name__)

__all__ = ("NetSuiteRestlet",)


class NetSuiteRestlet(RestApiBase):
    def __init__(
        self,
        config: Config,
        *,
        default_timeout: int = 60,
        concurrent_requests: int = 10,
    ):
        self._config = config
        self._default_timeout = default_timeout
        self._concurrent_requests = concurrent_requests

    @cached_property
    def hostname(self) -> str:
        return self._make_hostname()

    async def get(self, script_id: int, *, deploy: int = 1, **request_kw):
        subpath = self._make_restlet_params(script_id, deploy)
        return await self._request("GET", subpath, **request_kw)

    async def post(self, script_id: int, *, deploy: int = 1, **request_kw):
        subpath = self._make_restlet_params(script_id, deploy)
        return await self._request("POST", subpath, **request_kw)

    async def put(self, script_id: int, *, deploy: int = 1, **request_kw):
        subpath = self._make_restlet_params(script_id, deploy)
        return await self._request("PUT", subpath, **request_kw)

    async def delete(self, script_id: int, *, deploy: int = 1, **request_kw):
        subpath = self._make_restlet_params(script_id, deploy)
        return await self._request("DELETE", subpath, **request_kw)

    def _make_restlet_params(self, script_id: int, deploy: int = 1) -> str:
        return f"?script={script_id}&deploy={deploy}"

    def _make_hostname(self):
        return f"{self._config.account_slugified}.restlets.api.netsuite.com"

    def _make_url(self, subpath: str) -> str:
        return f"https://{self.hostname}/app/site/hosting/restlet.nl{subpath}"
