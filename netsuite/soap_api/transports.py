import urllib.parse

from . import zeep

__all__ = ("AsyncNetSuiteTransport",)


# TODO: ASYNC! Maybe remove this custom transport?!?!


class AsyncNetSuiteTransport(zeep.transports.AsyncTransport):
    """
    NetSuite company-specific domain wrapper for zeep.transports.transport

    Latest NetSuite WSDL now uses relative definition addresses

    zeep maps reflective remote calls to the base WSDL address,
    rather than the dynamic subscriber domain

    Wrap the zeep transports service with our address modifications
    """

    def __init__(self, wsdl_url, *args, **kwargs):
        parsed = urllib.parse.urlparse(wsdl_url)
        self._netsuite_base_url = f"{parsed.scheme}://{parsed.netloc}"
        super().__init__(*args, **kwargs)

    def _fix_address(self, address):
        """Munge the address to the company-specific domain, not the default"""
        idx = address.index("/", 8)
        path = address[idx:]
        return f"{self._netsuite_base_url}{path}"

    async def get(self, address, params, headers):
        return await super().get(self._fix_address(address), params, headers)

    async def post(self, address, message, headers):
        return await super().post(self._fix_address(address), message, headers)
