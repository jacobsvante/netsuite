from functools import cached_property
from typing import Any, Dict, Optional

from .config import Config
from .rest_api import NetSuiteRestApi
from .restlet import NetSuiteRestlet
from .soap_api import NetSuiteSoapApi

__all__ = ("NetSuite",)


class NetSuite:
    def __init__(
        self,
        config: Config,
        *,
        soap_api_options: Optional[Dict[str, Any]] = None,
        rest_api_options: Optional[Dict[str, Any]] = None,
        restlet_options: Optional[Dict[str, Any]] = None,
    ):
        self._config = config
        self._soap_api_options = soap_api_options or {}
        self._rest_api_options = rest_api_options or {}
        self._restlet_options = restlet_options or {}

    @cached_property
    def rest_api(self) -> NetSuiteRestApi:
        return NetSuiteRestApi(self._config, **self._rest_api_options)

    @cached_property
    def soap_api(self) -> NetSuiteSoapApi:
        return NetSuiteSoapApi(self._config, **self._soap_api_options)

    @cached_property
    def restlet(self) -> NetSuiteRestlet:
        return NetSuiteRestlet(self._config, **self._restlet_options)
