"""Tests for the `WebServiceCall` decorator.

Regression tests for jacobsvante/netsuite#45 — the decorator previously
checked `isinstance(response, zeep.xsd.ComplexType)`, which is the schema
definition class. Real SOAP responses are `zeep.xsd.CompoundValue` instances,
so the check was always False and status validation / extraction were
silently skipped. The decorator was also a synchronous wrapper around async
SOAP methods, so even with the right isinstance check it would have received
a coroutine instead of a response.
"""

import pytest

from netsuite.soap_api.exceptions import NetsuiteResponseError
from netsuite.soap_api.zeep import ZEEP_INSTALLED

pytestmark = pytest.mark.skipif(not ZEEP_INSTALLED, reason="Requires zeep")

if ZEEP_INSTALLED:
    from zeep.xsd.valueobjects import CompoundValue

    from netsuite.soap_api.decorators import WebServiceCall


class _FakeResponse(CompoundValue):
    """A minimal CompoundValue-shaped object usable as both attribute container and mapping."""

    def __init__(self, **attrs):
        # Bypass CompoundValue.__init__ which expects an XSD type
        object.__setattr__(self, "_attrs", attrs)

    def __getattr__(self, name):
        attrs = object.__getattribute__(self, "_attrs")
        if name in attrs:
            return attrs[name]
        raise AttributeError(name)

    def __getitem__(self, key):
        return object.__getattribute__(self, "_attrs")[key]

    def __iter__(self):
        return iter(object.__getattribute__(self, "_attrs").values())


def _ok_status():
    return {"isSuccess": True, "statusDetail": []}


def _err_status(detail="boom"):
    return {"isSuccess": False, "statusDetail": detail}


@pytest.mark.asyncio
async def test_async_decorator_unwraps_path_and_extracts():
    """Decorator must descend `path` and apply `extract` for async SOAP methods."""

    inner = _FakeResponse(record={"id": 42}, status=_ok_status())
    outer = _FakeResponse(body=_FakeResponse(readResponse=inner))

    @WebServiceCall(
        "body.readResponse",
        extract=lambda resp: resp["record"],
    )
    async def fake_get(self):
        return outer

    result = await fake_get(object())
    assert result == {"id": 42}


@pytest.mark.asyncio
async def test_async_decorator_raises_on_failed_status():
    inner = _FakeResponse(record=None, status=_err_status("nope"))
    outer = _FakeResponse(body=_FakeResponse(readResponse=inner))

    @WebServiceCall("body.readResponse")
    async def fake_get(self):
        return outer

    with pytest.raises(NetsuiteResponseError):
        await fake_get(object())


@pytest.mark.asyncio
async def test_async_decorator_passes_through_non_soap_values():
    """If the wrapped function returns a non-CompoundValue (e.g. early-out []),
    the decorator should return it untouched without trying to walk `path`."""

    @WebServiceCall("body.readResponseList.readResponse")
    async def fake_getList(self):
        return []

    assert await fake_getList(object()) == []


@pytest.mark.asyncio
async def test_async_decorator_returns_default_when_path_missing():
    outer = _FakeResponse(body=_FakeResponse())  # no `getItemAvailabilityResult`

    @WebServiceCall(
        "body.getItemAvailabilityResult",
        extract=lambda resp: resp["itemAvailabilityList"]["itemAvailability"],
        default=[],
    )
    async def fake_getItemAvailability(self):
        return outer

    assert await fake_getItemAvailability(object()) == []


def test_sync_decorator_still_works():
    """Sync functions decorated with WebServiceCall should also process responses."""

    inner = _FakeResponse(record={"id": 7}, status=_ok_status())
    outer = _FakeResponse(body=_FakeResponse(readResponse=inner))

    @WebServiceCall(
        "body.readResponse",
        extract=lambda resp: resp["record"],
    )
    def fake_get_sync(self):
        return outer

    assert fake_get_sync(object()) == {"id": 7}
