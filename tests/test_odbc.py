# TODO need more expanded tests here
def test_expected_hostname(dummy_username_password_config):
    config = dummy_username_password_config
    assert config.auth.username == "username"
