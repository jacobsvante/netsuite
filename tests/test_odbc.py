# TODO need more expanded tests here
from netsuite import NetSuiteODBC


def test_tba(dummy_config):
    assert dummy_config.is_token_auth


def test_sandbox_account(dummy_config):
    assert dummy_config.is_sandbox
    assert dummy_config.account_number == "123456"
    assert dummy_config.account_slugified == "123456-sb1"


def test_production_account_extraction(dummy_config_with_production_account):
    assert "_SB" not in dummy_config_with_production_account.account
    assert dummy_config_with_production_account.account_number == "123456"
    assert dummy_config_with_production_account.is_sandbox is False
    assert dummy_config_with_production_account.account_slugified == "123456"


def test_username_auth(dummy_username_password_config):
    config = dummy_username_password_config

    assert config.auth.username == "username"
    assert type(config.auth.role) in [int, str]
    assert config.odbc_data_source in ["NetSuite.com", "NetSuite2.com"]
    assert config.odbc_driver == "{NetSuite Drivers 64bit}"
    assert not config.is_token_auth


def test_correct_config_auth_method(dummy_username_password_config):
    config = dummy_username_password_config
    ns = NetSuiteODBC(config)
    assert ns.hostname == "123456-sb1.connect.api.netsuite.com"
