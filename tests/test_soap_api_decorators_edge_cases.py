"""Edge-case tests for `WebServiceCall` not covered in
`test_soap_api_decorators.py`.

Focus: the list-status code path (TypeError when indexing the response with
"status" because it's iterable rather than a mapping), and the unset-default
re-raise."""

import pytest

from netsuite.soap_api.exceptions import NetsuiteResponseError
from netsuite.soap_api.zeep import ZEEP_INSTALLED

pytestmark = pytest.mark.skipif(not ZEEP_INSTALLED, reason="Requires zeep")

if ZEEP_INSTALLED:
    from zeep.xsd.valueobjects import CompoundValue

    from netsuite.soap_api.decorators import WebServiceCall


class _AttrAndItemResponse(CompoundValue):
    def __init__(self, **attrs):
        object.__setattr__(self, "_attrs", attrs)

    def __getattr__(self, name):
        attrs = object.__getattribute__(self, "_attrs")
        if name in attrs:
            return attrs[name]
        raise AttributeError(name)

    def __getitem__(self, key):
        return object.__getattribute__(self, "_attrs")[key]


@pytest.mark.asyncio
async def test_decorator_status_via_list_iteration_when_indexing_raises():
    """When path traversal lands on a plain list (e.g. a record list), the
    decorator's `response['status']` raises TypeError. It must then iterate
    the list and pull `status` from the first record."""

    record = _AttrAndItemResponse(status={"isSuccess": True, "statusDetail": []})
    # `body.records` resolves to a plain Python list — `list['status']`
    # raises TypeError, exercising the fallback iteration path.
    outer = _AttrAndItemResponse(body=_AttrAndItemResponse(records=[record]))

    @WebServiceCall("body.records", extract=lambda resp: list(resp))
    async def fake_op(self):
        return outer

    out = await fake_op(object())
    assert out == [record]


@pytest.mark.asyncio
async def test_decorator_status_via_list_iteration_propagates_error():
    record = _AttrAndItemResponse(
        status={"isSuccess": False, "statusDetail": "first record failed"}
    )
    outer = _AttrAndItemResponse(body=_AttrAndItemResponse(records=[record]))

    @WebServiceCall("body.records")
    async def fake_op(self):
        return outer

    with pytest.raises(NetsuiteResponseError):
        await fake_op(object())


@pytest.mark.asyncio
async def test_decorator_reraises_attribute_error_when_default_unset():
    """If walking `path` hits an AttributeError and no `default` was
    supplied, the original AttributeError should propagate rather than be
    silently swallowed."""

    outer = _AttrAndItemResponse(body=_AttrAndItemResponse())  # no `readResponse`

    @WebServiceCall("body.readResponse")  # no default
    async def fake_get(self):
        return outer

    with pytest.raises(AttributeError):
        await fake_get(object())
