from netsuite import NetSuiteRestlet


def test_expected_hostname(dummy_config):
    restlet = NetSuiteRestlet(dummy_config)
    assert restlet.hostname == "123456-sb1.restlets.api.netsuite.com"
