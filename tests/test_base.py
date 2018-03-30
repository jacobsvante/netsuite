import pytest
import netsuite


@pytest.fixture
def dummy_config():
    return {
        'account': '123456',
        'consumer_key': 'abcdefghijklmnopqrstuvwxyz0123456789',
        'consumer_secret': 'abcdefghijklmnopqrstuvwxyz0123456789',
        'token_id': 'abcdefghijklmnopqrstuvwxyz0123456789',
        'token_secret': 'abcdefghijklmnopqrstuvwxyz0123456789',
    }


def test_netsuite_hostname(dummy_config):
    ns = netsuite.NetSuite(dummy_config)
    assert ns.hostname == 'webservices.sandbox.netsuite.com'


def test_netsuite_wsdl_url(dummy_config):
    ns = netsuite.NetSuite(dummy_config)
    assert ns.wsdl_url == 'https://webservices.sandbox.netsuite.com/wsdl/v2017_2_0/netsuite.wsdl'
