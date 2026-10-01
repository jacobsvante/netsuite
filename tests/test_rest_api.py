import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from netsuite import NetSuiteRestApi
from netsuite.exceptions import NetsuiteAPIRequestError


def test_expected_hostname(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    assert rest_api.hostname == "123456-sb1.suitetalk.api.netsuite.com"


@pytest.mark.asyncio
async def test_suiteql_posts_to_query_endpoint(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={"items": []})  # type: ignore[method-assign]
    await rest_api.suiteql(q="SELECT id FROM customer", limit=50, offset=10)
    rest_api._request.assert_awaited_once()
    args, kwargs = rest_api._request.await_args
    assert args == ("POST", "/query/v1/suiteql")
    assert kwargs["json"] == {"q": "SELECT id FROM customer"}
    assert kwargs["params"] == {"limit": 50, "offset": 10}
    assert kwargs["headers"]["Prefer"] == "transient"


def _page(items, *, has_more, next_url=None):
    page = {"items": items, "hasMore": has_more, "links": []}
    if next_url is not None:
        page["links"].append({"rel": "next", "href": next_url})
    return page


@pytest.mark.asyncio
async def test_suiteql_paginated_follows_next_link_until_exhausted(dummy_config):
    """Regression test for jacobsvante/netsuite#42 — pagination must walk the
    `next` link until `hasMore` is False, without re-sending the original
    `params` (which would double-encode offset/limit)."""
    rest_api = NetSuiteRestApi(dummy_config)
    pages = [
        _page([1, 2], has_more=True, next_url="https://example.com/page2"),
        _page([3, 4], has_more=True, next_url="https://example.com/page3"),
        _page([5], has_more=False),
    ]
    rest_api._request = AsyncMock(side_effect=pages)  # type: ignore[method-assign]

    collected = []
    async for page in rest_api.suiteql_paginated(
        q="SELECT id FROM transaction", limit=2
    ):
        collected.extend(page["items"])

    assert collected == [1, 2, 3, 4, 5]
    assert rest_api._request.await_count == 3

    # Subsequent calls must use the absolute `url` from the next link, and
    # must NOT re-pass `params` (NetSuite's next URL already encodes them).
    second_call_kwargs = rest_api._request.await_args_list[1].kwargs
    assert second_call_kwargs.get("url") == "https://example.com/page2"
    assert "params" not in second_call_kwargs


@pytest.mark.asyncio
async def test_suiteql_paginated_stops_when_hasmore_false_on_first_page(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(  # type: ignore[method-assign]
        return_value=_page([1], has_more=False)
    )
    pages = [page async for page in rest_api.suiteql_paginated(q="SELECT 1")]
    assert len(pages) == 1
    rest_api._request.assert_awaited_once()


@pytest.mark.asyncio
async def test_suiteql_paginated_stops_when_no_next_link(dummy_config):
    """`hasMore=true` but no `rel=next` link should still terminate cleanly."""
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(  # type: ignore[method-assign]
        return_value=_page([1], has_more=True)  # no next_url
    )
    pages = [page async for page in rest_api.suiteql_paginated(q="SELECT 1")]
    assert len(pages) == 1


@pytest.mark.asyncio
async def test_suiteql_warns_on_order_by_with_small_limit(dummy_config, caplog):
    """Regression test for jacobsvante/netsuite#29: warn when an `ORDER BY`
    SuiteQL query is combined with a limit that may trigger NetSuite's
    zero-row quirk."""
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={"items": []})  # type: ignore[method-assign]
    with caplog.at_level(logging.WARNING, logger="netsuite.rest_api"):
        await rest_api.suiteql(q="SELECT id FROM subsidiary ORDER BY id")
    assert any("ORDER BY" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_suiteql_quiet_when_order_by_with_safe_limit(dummy_config, caplog):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={"items": []})  # type: ignore[method-assign]
    with caplog.at_level(logging.WARNING, logger="netsuite.rest_api"):
        await rest_api.suiteql(q="SELECT id FROM subsidiary ORDER BY id", limit=1000)
    assert not any("ORDER BY" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_suiteql_quiet_when_no_order_by(dummy_config, caplog):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={"items": []})  # type: ignore[method-assign]
    with caplog.at_level(logging.WARNING, logger="netsuite.rest_api"):
        await rest_api.suiteql(q="SELECT id FROM subsidiary")
    assert not any("ORDER BY" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_suiteql_order_by_detection_is_case_insensitive(dummy_config, caplog):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={"items": []})  # type: ignore[method-assign]
    with caplog.at_level(logging.WARNING, logger="netsuite.rest_api"):
        await rest_api.suiteql(q="select id from subsidiary order by id")
    assert any("ORDER BY" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_suiteql_order_by_detection_ignores_substrings(dummy_config, caplog):
    """`order_by_id` as a column name shouldn't trigger the warning."""
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={"items": []})  # type: ignore[method-assign]
    with caplog.at_level(logging.WARNING, logger="netsuite.rest_api"):
        await rest_api.suiteql(q="SELECT order_by_id FROM custom_table")
    assert not any("ORDER BY" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# 2026.1 REST web services operations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attach_posts_to_attach_endpoint_with_empty_body(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    result = await rest_api.attach("customer", "660", "contact", "106")
    assert result is None
    args, kwargs = rest_api._request.await_args
    assert args == (
        "POST",
        "/record/v1/customer/660/!attach/contact/106",
    )
    # Body defaults to an empty object when no role is given.
    assert kwargs["json"] == {}


@pytest.mark.asyncio
async def test_attach_includes_role_when_provided(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    await rest_api.attach("customer", "660", "contact", "106", role={"id": "-10"})
    _, kwargs = rest_api._request.await_args
    assert kwargs["json"] == {"role": {"id": "-10"}}


@pytest.mark.asyncio
async def test_attach_supports_external_ids(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    await rest_api.attach("customer", "eid:JOHN_DOE42", "contact", "eid:user1")
    args, _ = rest_api._request.await_args
    assert args[1] == ("/record/v1/customer/eid:JOHN_DOE42/!attach/contact/eid:user1")


@pytest.mark.asyncio
async def test_detach_posts_to_detach_endpoint_without_body(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    await rest_api.detach("opportunity", "379", "file", "398")
    args, kwargs = rest_api._request.await_args
    assert args == (
        "POST",
        "/record/v1/opportunity/379/!detach/file/398",
    )
    # Detach sends no body at all.
    assert "json" not in kwargs


@pytest.mark.asyncio
async def test_create_form_posts_transform_with_accept_header(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={"id": "1"})  # type: ignore[method-assign]
    await rest_api.create_form("salesOrder", "1", "itemFulfillment")
    args, kwargs = rest_api._request.await_args
    assert args == (
        "POST",
        "/record/v1/salesOrder/1/!transform/itemFulfillment",
    )
    assert (
        kwargs["headers"]["Accept"]
        == "application/vnd.oracle.resource+json; type=create-form"
    )
    assert kwargs["json"] == {}


@pytest.mark.asyncio
async def test_select_options_uses_post_for_new_instance(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={})  # type: ignore[method-assign]
    await rest_api.select_options("customer", "entitystatus")
    args, kwargs = rest_api._request.await_args
    assert args == ("POST", "/record/v1/customer")
    assert kwargs["params"]["fields"] == "entitystatus"
    assert (
        kwargs["headers"]["Accept"]
        == "application/vnd.oracle.resource+json; type=select-options"
    )


@pytest.mark.asyncio
async def test_select_options_uses_patch_for_existing_instance(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={})  # type: ignore[method-assign]
    await rest_api.select_options(
        "advInterCompanyJournalEntry",
        ["line.dueToFromSubsidiary", "subsidiary"],
        record_id="5",
        body={"subsidiary": {"id": 1}},
    )
    args, kwargs = rest_api._request.await_args
    assert args == ("PATCH", "/record/v1/advInterCompanyJournalEntry/5")
    # Multiple fields are comma-joined; dependent values ride in the body.
    assert kwargs["params"]["fields"] == "line.dueToFromSubsidiary,subsidiary"
    assert kwargs["json"] == {"subsidiary": {"id": 1}}


@pytest.mark.asyncio
async def test_batch_sets_async_headers_and_returns_job_location(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    job_url = "https://x.suitetalk.api.netsuite.com/services/rest/async/v1/job/42"
    fake_resp = SimpleNamespace(
        status_code=202,
        text="",
        headers={"Location": job_url},
    )
    rest_api._request_impl = AsyncMock(return_value=fake_resp)  # type: ignore[method-assign]
    result = await rest_api.batch(
        "salesOrder",
        [{"name": "item 1"}, {"name": "item 2"}],
        idempotency_key="abc-123",
    )
    args, kwargs = rest_api._request_impl.await_args
    assert args == ("POST", "/record/v1/salesOrder")
    assert kwargs["headers"]["Prefer"] == "respond-async"
    assert (
        kwargs["headers"]["Content-Type"]
        == "application/vnd.oracle.resource+json; type=collection"
    )
    assert kwargs["headers"]["X-NetSuite-idempotency-key"] == "abc-123"
    assert kwargs["json"] == {"items": [{"name": "item 1"}, {"name": "item 2"}]}
    assert result == {"status_code": 202, "location": job_url, "body": None}


@pytest.mark.asyncio
async def test_batch_rejects_non_write_methods(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request_impl = AsyncMock()  # type: ignore[method-assign]
    with pytest.raises(ValueError, match="batch\\(\\) method must be"):
        await rest_api.batch("salesOrder", [], method="GET")
    rest_api._request_impl.assert_not_awaited()


@pytest.mark.asyncio
async def test_batch_raises_on_error_status(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    fake_resp = SimpleNamespace(status_code=400, text="bad request", headers={})
    rest_api._request_impl = AsyncMock(return_value=fake_resp)  # type: ignore[method-assign]
    with pytest.raises(NetsuiteAPIRequestError):
        await rest_api.batch("salesOrder", [{"name": "x"}], method="PATCH")


# ---------------------------------------------------------------------------
# create_record — POST a record and return the new ID from the Location header
# ---------------------------------------------------------------------------


def _created_response(location, *, status_code=204):
    # NetSuite answers a create with 204 No Content and a Location header
    # pointing at the new record. httpx.Headers is case-insensitive, which
    # is what the real response uses.
    return SimpleNamespace(
        status_code=status_code,
        text="",
        headers=httpx.Headers({"Location": location} if location else {}),
    )


@pytest.mark.asyncio
async def test_create_record_posts_data_to_collection_endpoint(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    loc = "https://x.suitetalk.api.netsuite.com/services/rest/record/v1/customer/647"
    rest_api._request_impl = AsyncMock(  # type: ignore[method-assign]
        return_value=_created_response(loc)
    )
    data = {"companyName": "Acme", "subsidiary": {"id": "1"}}
    await rest_api.create_record("customer", data)
    args, kwargs = rest_api._request_impl.await_args
    assert args == ("POST", "/record/v1/customer")
    assert kwargs["json"] == data


@pytest.mark.asyncio
async def test_create_record_returns_int_for_numeric_id(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    loc = "https://x.suitetalk.api.netsuite.com/services/rest/record/v1/customer/647"
    rest_api._request_impl = AsyncMock(  # type: ignore[method-assign]
        return_value=_created_response(loc)
    )
    result = await rest_api.create_record("customer", {})
    assert result == 647
    assert isinstance(result, int)


@pytest.mark.asyncio
async def test_create_record_returns_str_for_external_id(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    loc = (
        "https://x.suitetalk.api.netsuite.com/services/rest/record/v1/"
        "customer/eid:ACME_42"
    )
    rest_api._request_impl = AsyncMock(  # type: ignore[method-assign]
        return_value=_created_response(loc)
    )
    result = await rest_api.create_record("customer", {})
    assert result == "eid:ACME_42"


@pytest.mark.asyncio
async def test_create_record_ignores_query_and_trailing_slash(dummy_config):
    """Regression vs the original `/([^/]+)$` regex, which would return the
    querystring or an empty segment. The ID is the last real path segment."""
    rest_api = NetSuiteRestApi(dummy_config)
    loc = (
        "https://x.suitetalk.api.netsuite.com/services/rest/record/v1/"
        "salesOrder/980/?expandSubResources=true"
    )
    rest_api._request_impl = AsyncMock(  # type: ignore[method-assign]
        return_value=_created_response(loc)
    )
    result = await rest_api.create_record("salesOrder", {})
    assert result == 980


@pytest.mark.asyncio
async def test_create_record_returns_none_without_location_header(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request_impl = AsyncMock(  # type: ignore[method-assign]
        return_value=_created_response(None)
    )
    result = await rest_api.create_record("customer", {})
    assert result is None


@pytest.mark.asyncio
async def test_create_record_raises_on_error_status(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    fake_resp = SimpleNamespace(status_code=400, text="bad", headers=httpx.Headers())
    rest_api._request_impl = AsyncMock(  # type: ignore[method-assign]
        return_value=fake_resp
    )
    with pytest.raises(NetsuiteAPIRequestError):
        await rest_api.create_record("customer", {"bad": "data"})


@pytest.mark.asyncio
async def test_batch_parses_json_body_when_present(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    fake_resp = SimpleNamespace(
        status_code=200,
        text='{"results": [1, 2]}',
        headers={"Location": "https://x/job/1"},
    )
    rest_api._request_impl = AsyncMock(return_value=fake_resp)  # type: ignore[method-assign]
    result = await rest_api.batch("salesOrder", [{"name": "x"}])
    assert result["body"] == {"results": [1, 2]}


@pytest.mark.asyncio
async def test_batch_tolerates_non_json_body(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    fake_resp = SimpleNamespace(status_code=200, text="not json", headers={})
    rest_api._request_impl = AsyncMock(return_value=fake_resp)  # type: ignore[method-assign]
    result = await rest_api.batch("salesOrder", [{"name": "x"}])
    assert result["body"] is None


# ---------------------------------------------------------------------------
# Plain HTTP verbs + metadata helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_delegates_to_request_impl(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request_impl = AsyncMock(return_value="resp")  # type: ignore[method-assign]
    out = await rest_api.request("GET", "/x", params={"a": 1})
    assert out == "resp"
    args, _ = rest_api._request_impl.await_args
    assert args == ("GET", "/x")


@pytest.mark.parametrize(
    "verb,method",
    [
        ("get", "GET"),
        ("post", "POST"),
        ("put", "PUT"),
        ("patch", "PATCH"),
        ("delete", "DELETE"),
    ],
)
@pytest.mark.asyncio
async def test_http_verbs_delegate_to_request(dummy_config, verb, method):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={"ok": 1})  # type: ignore[method-assign]
    out = await getattr(rest_api, verb)("/sub")
    assert out == {"ok": 1}
    args, _ = rest_api._request.await_args
    assert args[0] == method
    assert args[1] == "/sub"


@pytest.mark.asyncio
async def test_jsonschema_sets_accept_header(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={})  # type: ignore[method-assign]
    await rest_api.jsonschema("salesOrder")
    args, kwargs = rest_api._request.await_args
    assert args == ("GET", "/record/v1/metadata-catalog/salesOrder")
    assert kwargs["headers"]["Accept"] == "application/schema+json"


@pytest.mark.asyncio
async def test_token_info_overrides_url_to_restlets_host(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={})  # type: ignore[method-assign]
    await rest_api.token_info()
    _, kwargs = rest_api._request.await_args
    assert kwargs["url"].endswith("/rest/tokeninfo")
    assert "restlets.api.netsuite.com" in kwargs["url"]


@pytest.mark.asyncio
async def test_openapi_sets_accept_and_select_param(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={})  # type: ignore[method-assign]
    await rest_api.openapi(["customer", "invoice"])
    args, kwargs = rest_api._request.await_args
    assert args == ("GET", "/record/v1/metadata-catalog")
    assert kwargs["headers"]["Accept"] == "application/swagger+json"
    assert kwargs["params"]["select"] == "customer,invoice"


@pytest.mark.asyncio
async def test_openapi_without_record_types_omits_select(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    rest_api._request = AsyncMock(return_value={})  # type: ignore[method-assign]
    await rest_api.openapi()
    _, kwargs = rest_api._request.await_args
    assert "select" not in kwargs["params"]


def test_make_url_and_default_headers(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    url = rest_api._make_url("/record/v1/customer")
    assert url == (
        "https://123456-sb1.suitetalk.api.netsuite.com"
        "/services/rest/record/v1/customer"
    )
    headers = rest_api._make_default_headers()
    assert headers["Content-Type"] == "application/json"
    assert headers["X-NetSuite-PropertyNameValidation"] == "error"
