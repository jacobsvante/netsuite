"""Tests for `NetSuiteRestlet`. Previously only `hostname` was tested."""

from unittest.mock import AsyncMock

import pytest

from netsuite import NetSuiteRestlet


def test_expected_hostname(dummy_config):
    restlet = NetSuiteRestlet(dummy_config)
    assert restlet.hostname == "123456-sb1.restlets.api.netsuite.com"


def test_hostname_for_production_account(dummy_config_with_production_account):
    restlet = NetSuiteRestlet(dummy_config_with_production_account)
    assert restlet.hostname == "123456.restlets.api.netsuite.com"


def test_make_url_includes_restlet_path(dummy_config):
    restlet = NetSuiteRestlet(dummy_config)
    url = restlet._make_url("?script=42&deploy=1")
    assert (
        url
        == "https://123456-sb1.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=42&deploy=1"
    )


def test_make_restlet_params_default_deploy(dummy_config):
    restlet = NetSuiteRestlet(dummy_config)
    assert restlet._make_restlet_params(123) == "?script=123&deploy=1"


def test_make_restlet_params_custom_deploy(dummy_config):
    restlet = NetSuiteRestlet(dummy_config)
    assert restlet._make_restlet_params(123, deploy=7) == "?script=123&deploy=7"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "verb,expected_method",
    [("get", "GET"), ("post", "POST"), ("put", "PUT"), ("delete", "DELETE")],
)
async def test_each_verb_calls_request_with_script_subpath(
    dummy_config, verb, expected_method
):
    restlet = NetSuiteRestlet(dummy_config)
    restlet._request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    method = getattr(restlet, verb)
    await method(123, deploy=2, json={"foo": "bar"})
    restlet._request.assert_awaited_once()
    args, kwargs = restlet._request.await_args
    assert args == (expected_method, "?script=123&deploy=2")
    assert kwargs["json"] == {"foo": "bar"}


@pytest.mark.asyncio
async def test_default_deploy_is_one(dummy_config):
    restlet = NetSuiteRestlet(dummy_config)
    restlet._request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    await restlet.get(987)
    args, _ = restlet._request.await_args
    assert args == ("GET", "?script=987&deploy=1")
