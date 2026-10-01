"""Tests for the HTTP 429 (`CONCURRENCY_LIMIT_EXCEEDED`) retry in
`RestApiBase._request_impl`."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from netsuite import NetSuite
from netsuite.exceptions import NetsuiteAPIRequestError
from netsuite.rest_api import NetSuiteRestApi
from netsuite.rest_api_base import (
    _RETRY_BACKOFF_MAX_SECONDS,
    DEFAULT_MAX_RETRIES_ON_429,
    RestApiBase,
)
from netsuite.restlet import NetSuiteRestlet

_CONCURRENCY_BODY = (
    '{"o:errorDetails": [{"o:errorCode": "CONCURRENCY_LIMIT_EXCEEDED"}]}'
)


class _ConcreteApi(RestApiBase):
    def __init__(self, config, max_retries_on_429=DEFAULT_MAX_RETRIES_ON_429):
        self._config = config
        self._default_timeout = 10
        self._concurrent_requests = 5
        self._max_retries_on_429 = max_retries_on_429

    def _make_url(self, subpath):
        return f"https://example.com{subpath}"


def _resp(status_code, text="{}", headers=None):
    return httpx.Response(
        status_code,
        content=text.encode("utf-8"),
        headers=headers or {},
        request=httpx.Request("GET", "https://example.com/x"),
    )


def _scripted_client(responses, calls):
    """An `httpx.AsyncClient` stand-in that returns `responses` in order."""
    queue = list(responses)

    class _FakeClient:
        def __init__(self, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def request(self, **kw):
            calls.append(kw)
            return queue.pop(0)

    return _FakeClient


@pytest.fixture
def no_sleep():
    with patch("netsuite.rest_api_base.asyncio.sleep", new=AsyncMock()) as sleep:
        yield sleep


@pytest.mark.asyncio
async def test_retries_429_then_returns_success(dummy_config, no_sleep):
    api = _ConcreteApi(dummy_config)
    calls: list = []
    responses = [_resp(429, _CONCURRENCY_BODY), _resp(429), _resp(200, '{"ok": 1}')]
    with patch(
        "netsuite.rest_api_base.httpx.AsyncClient",
        _scripted_client(responses, calls),
    ):
        assert await api._request("POST", "/x", json={"q": "SELECT 1"}) == {"ok": 1}

    assert len(calls) == 3
    assert no_sleep.await_count == 2
    # Each attempt re-sends the same body.
    assert calls[0]["data"] == calls[2]["data"]


@pytest.mark.asyncio
async def test_each_attempt_gets_fresh_auth(dummy_config, no_sleep):
    """OAuth 1.0a nonces/timestamps must not be replayed across attempts."""
    api = _ConcreteApi(dummy_config)
    calls: list = []
    with patch(
        "netsuite.rest_api_base.httpx.AsyncClient",
        _scripted_client([_resp(429), _resp(200)], calls),
    ), patch.object(api, "_make_auth", side_effect=["auth-1", "auth-2"]):
        await api._request_impl("GET", "/x")

    assert [c["auth"] for c in calls] == ["auth-1", "auth-2"]


@pytest.mark.asyncio
async def test_gives_up_after_max_retries_and_raises(dummy_config, no_sleep):
    api = _ConcreteApi(dummy_config, max_retries_on_429=2)
    calls: list = []
    with patch(
        "netsuite.rest_api_base.httpx.AsyncClient",
        _scripted_client([_resp(429, _CONCURRENCY_BODY)] * 3, calls),
    ):
        with pytest.raises(NetsuiteAPIRequestError) as excinfo:
            await api._request("GET", "/x")

    assert len(calls) == 3  # first try + 2 retries
    assert excinfo.value.status_code == 429
    assert "CONCURRENCY_LIMIT_EXCEEDED" in excinfo.value.response_text


@pytest.mark.asyncio
async def test_zero_retries_disables_retry(dummy_config, no_sleep):
    api = _ConcreteApi(dummy_config, max_retries_on_429=0)
    calls: list = []
    with patch(
        "netsuite.rest_api_base.httpx.AsyncClient",
        _scripted_client([_resp(429)], calls),
    ):
        resp = await api._request_impl("GET", "/x")

    assert resp.status_code == 429
    assert len(calls) == 1
    no_sleep.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 500, 503])
async def test_other_errors_are_not_retried(dummy_config, no_sleep, status_code):
    api = _ConcreteApi(dummy_config)
    calls: list = []
    with patch(
        "netsuite.rest_api_base.httpx.AsyncClient",
        _scripted_client([_resp(status_code)], calls),
    ):
        resp = await api._request_impl("GET", "/x")

    assert resp.status_code == status_code
    assert len(calls) == 1
    no_sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_waits_for_backoff_delay(dummy_config, no_sleep):
    api = _ConcreteApi(dummy_config)
    with patch(
        "netsuite.rest_api_base.httpx.AsyncClient",
        _scripted_client([_resp(429, headers={"Retry-After": "3"}), _resp(200)], []),
    ):
        await api._request_impl("GET", "/x")

    no_sleep.assert_awaited_once_with(3.0)


def test_retry_delay_honours_numeric_retry_after():
    assert RestApiBase._retry_delay(_resp(429, headers={"Retry-After": "7"}), 1) == 7.0


def test_retry_delay_caps_retry_after():
    resp = _resp(429, headers={"Retry-After": "3600"})
    assert RestApiBase._retry_delay(resp, 1) == _RETRY_BACKOFF_MAX_SECONDS


@pytest.mark.parametrize(
    "attempt, low, high", [(1, 1.0, 2.0), (2, 2.0, 3.0), (3, 4.0, 5.0)]
)
def test_retry_delay_is_exponential_with_jitter(attempt, low, high):
    delay = RestApiBase._retry_delay(_resp(429), attempt)
    assert low <= delay <= high


def test_retry_delay_ignores_http_date_retry_after():
    resp = _resp(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"})
    assert 1.0 <= RestApiBase._retry_delay(resp, 1) <= 2.0


def test_retry_delay_is_capped():
    assert RestApiBase._retry_delay(_resp(429), 20) == _RETRY_BACKOFF_MAX_SECONDS


@pytest.mark.parametrize("cls", [NetSuiteRestApi, NetSuiteRestlet])
def test_max_retries_is_configurable_per_client(dummy_config, cls):
    assert cls(dummy_config)._max_retries_on_429 == DEFAULT_MAX_RETRIES_ON_429
    assert cls(dummy_config, max_retries_on_429=0)._max_retries_on_429 == 0


def test_max_retries_flows_through_netsuite_facade(dummy_config):
    ns = NetSuite(
        dummy_config,
        rest_api_options={"max_retries_on_429": 1},
        restlet_options={"max_retries_on_429": 2},
    )
    assert ns.rest_api._max_retries_on_429 == 1
    assert ns.restlet._max_retries_on_429 == 2
