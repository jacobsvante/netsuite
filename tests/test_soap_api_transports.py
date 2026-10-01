"""Tests for `AsyncNetSuiteTransport` — the zeep transport that forces
each request to the account-specific NetSuite subdomain."""

from unittest.mock import AsyncMock, patch

import pytest

from netsuite.soap_api.transports import AsyncNetSuiteTransport
from netsuite.soap_api.zeep import ZEEP_INSTALLED

pytestmark = pytest.mark.skipif(not ZEEP_INSTALLED, reason="Requires zeep")


def test_init_extracts_base_url_from_wsdl_url():
    transport = AsyncNetSuiteTransport(
        "https://123-sb1.suitetalk.api.netsuite.com/wsdl/v2021_1_0/netsuite.wsdl",
    )
    assert transport._netsuite_base_url == "https://123-sb1.suitetalk.api.netsuite.com"


def test_init_handles_url_without_path():
    transport = AsyncNetSuiteTransport("https://example.com")
    assert transport._netsuite_base_url == "https://example.com"


def test_fix_address_swaps_default_host_for_account_host():
    transport = AsyncNetSuiteTransport(
        "https://123-sb1.suitetalk.api.netsuite.com/wsdl/v2021_1_0/netsuite.wsdl",
    )
    assert (
        transport._fix_address(
            "https://webservices.netsuite.com/services/NetSuitePort_2021_1"
        )
        == "https://123-sb1.suitetalk.api.netsuite.com/services/NetSuitePort_2021_1"
    )


def test_fix_address_preserves_query_string():
    transport = AsyncNetSuiteTransport(
        "https://acct.suitetalk.api.netsuite.com/wsdl/v2021_1_0/netsuite.wsdl",
    )
    fixed = transport._fix_address(
        "https://webservices.netsuite.com/services/NetSuitePort_2021_1?wsdl"
    )
    assert (
        fixed
        == "https://acct.suitetalk.api.netsuite.com/services/NetSuitePort_2021_1?wsdl"
    )


@pytest.mark.asyncio
async def test_get_passes_through_fixed_address():
    transport = AsyncNetSuiteTransport(
        "https://acct.suitetalk.api.netsuite.com/wsdl/v.wsdl",
    )
    with patch(
        "zeep.transports.AsyncTransport.get",
        new_callable=AsyncMock,
        return_value="resp",
    ) as parent_get:
        result = await transport.get(
            "https://webservices.netsuite.com/services/foo",
            params={"k": "v"},
            headers={"H": "1"},
        )
    assert result == "resp"
    parent_get.assert_awaited_once_with(
        "https://acct.suitetalk.api.netsuite.com/services/foo",
        {"k": "v"},
        {"H": "1"},
    )


@pytest.mark.asyncio
async def test_post_passes_through_fixed_address():
    transport = AsyncNetSuiteTransport(
        "https://acct.suitetalk.api.netsuite.com/wsdl/v.wsdl",
    )
    with patch(
        "zeep.transports.AsyncTransport.post",
        new_callable=AsyncMock,
        return_value="resp",
    ) as parent_post:
        result = await transport.post(
            "https://webservices.netsuite.com/services/foo",
            "<xml/>",
            {"H": "1"},
        )
    assert result == "resp"
    parent_post.assert_awaited_once_with(
        "https://acct.suitetalk.api.netsuite.com/services/foo",
        "<xml/>",
        {"H": "1"},
    )
