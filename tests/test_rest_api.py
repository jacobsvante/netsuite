from netsuite import NetSuiteRestApi


def test_expected_hostname(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    assert rest_api.hostname == "123456-sb1.suitetalk.api.netsuite.com"
