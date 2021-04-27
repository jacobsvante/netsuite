import pytest

from netsuite import Config, NetSuiteSoapApi


@pytest.fixture
def dummy_config():
    return Config(
        account="123456",
        auth={
            "consumer_key": "abcdefghijklmnopqrstuvwxyz0123456789",
            "consumer_secret": "abcdefghijklmnopqrstuvwxyz0123456789",
            "token_id": "abcdefghijklmnopqrstuvwxyz0123456789",
            "token_secret": "abcdefghijklmnopqrstuvwxyz0123456789",
        },
    )


def test_netsuite_hostname(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config)
    assert soap_api.hostname == "123456.suitetalk.api.netsuite.com"


def test_netsuite_wsdl_url(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config)
    assert (
        soap_api.wsdl_url
        == "https://123456.suitetalk.api.netsuite.com/wsdl/v2021_1_0/netsuite.wsdl"
    )
