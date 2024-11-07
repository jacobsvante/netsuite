import pytest

from netsuite import NetSuiteSoapApi
from netsuite.soap_api.zeep import ZEEP_INSTALLED

pytestmark = pytest.mark.skipif(not ZEEP_INSTALLED, reason="Requires zeep")


def test_netsuite_hostname(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config)
    assert soap_api.hostname == "123456-sb1.suitetalk.api.netsuite.com"


def test_netsuite_wsdl_url(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config)
    assert (
        soap_api.wsdl_url
        == "https://123456-sb1.suitetalk.api.netsuite.com/wsdl/v2024_2_0/netsuite.wsdl"
    )


def test_netsuite_transport_initialization(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config)
    soap_api._generate_transport()
