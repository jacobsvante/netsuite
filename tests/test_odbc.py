# TODO need more expanded tests here


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
    assert not config.is_token_auth
