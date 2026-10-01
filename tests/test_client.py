"""Tests for the NetSuite facade — the cached_property accessors that lazily
construct the REST, Restlet, and SOAP sub-clients with their options.
"""

import warnings

import pytest

from netsuite import NetSuite
from netsuite.rest_api import NetSuiteRestApi
from netsuite.restlet import NetSuiteRestlet
from netsuite.soap_api.zeep import ZEEP_INSTALLED


def test_init_defaults_empty_option_dicts(dummy_config):
    ns = NetSuite(dummy_config)
    assert ns._rest_api_options == {}
    assert ns._soap_api_options == {}
    assert ns._restlet_options == {}


def test_rest_api_is_cached_and_receives_options(dummy_config):
    ns = NetSuite(dummy_config, rest_api_options={"default_timeout": 5})
    api = ns.rest_api
    assert isinstance(api, NetSuiteRestApi)
    assert api._default_timeout == 5
    # cached_property: same instance on second access
    assert ns.rest_api is api


def test_restlet_is_cached(dummy_config):
    ns = NetSuite(dummy_config)
    restlet = ns.restlet
    assert isinstance(restlet, NetSuiteRestlet)
    assert ns.restlet is restlet


@pytest.mark.skipif(not ZEEP_INSTALLED, reason="Requires zeep")
def test_soap_api_is_constructed(dummy_config):
    ns = NetSuite(dummy_config)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        soap = ns.soap_api
    assert ns.soap_api is soap
