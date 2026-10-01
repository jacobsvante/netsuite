"""Tests for `netsuite.config` — `Config` properties and `from_env` /
`from_ini` constructors."""

from textwrap import dedent

import pytest

from netsuite.config import Config, TokenAuth, UsernamePasswordAuth

# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


def test_is_token_auth_true(dummy_config):
    assert dummy_config.is_token_auth is True


def test_is_token_auth_false_for_username_password(dummy_username_password_config):
    assert dummy_username_password_config.is_token_auth is False


@pytest.mark.parametrize(
    "account,expected",
    [
        ("123456", False),
        ("123456_SB1", True),
        ("123456_SB2", True),
        ("ABCDE", False),
        ("123456_SB10", True),
    ],
)
def test_is_sandbox(account, expected, dummy_config):
    config = Config(account=account, auth=dummy_config.auth)
    assert config.is_sandbox is expected


def test_account_number_strips_sandbox_suffix(dummy_config):
    assert (
        Config(account="123456_SB1", auth=dummy_config.auth).account_number == "123456"
    )
    assert Config(account="123456", auth=dummy_config.auth).account_number == "123456"


def test_account_slugified_lowercases_and_replaces_underscore(dummy_config):
    assert (
        Config(account="123456_SB1", auth=dummy_config.auth).account_slugified
        == "123456-sb1"
    )


# ---------------------------------------------------------------------------
# `_reorganize_auth_keys` — splits flat dicts into top-level + nested `auth`
# ---------------------------------------------------------------------------


def test_reorganize_auth_keys_splits_token_fields():
    raw = {
        "account": "123456",
        "consumer_key": "ck",
        "consumer_secret": "cs",
        "token_id": "ti",
        "token_secret": "ts",
        "log_level": "DEBUG",
    }
    out = Config._reorganize_auth_keys(raw)
    assert out["account"] == "123456"
    assert out["log_level"] == "DEBUG"
    assert out["auth"] == {
        "consumer_key": "ck",
        "consumer_secret": "cs",
        "token_id": "ti",
        "token_secret": "ts",
    }


def test_reorganize_auth_keys_splits_username_password_fields():
    raw = {"account": "123456", "username": "u", "password": "p"}
    out = Config._reorganize_auth_keys(raw)
    assert out["account"] == "123456"
    assert out["auth"] == {"username": "u", "password": "p"}


def test_reorganize_auth_keys_handles_no_auth_fields():
    out = Config._reorganize_auth_keys({"account": "123456"})
    assert out == {"account": "123456", "auth": {}}


# ---------------------------------------------------------------------------
# `Config.from_env`
# ---------------------------------------------------------------------------


def test_from_env_builds_token_config(monkeypatch):
    monkeypatch.setenv("NETSUITE_ACCOUNT", "999_SB1")
    monkeypatch.setenv("NETSUITE_CONSUMER_KEY", "ck" * 18)
    monkeypatch.setenv("NETSUITE_CONSUMER_SECRET", "cs" * 18)
    monkeypatch.setenv("NETSUITE_TOKEN_ID", "ti" * 18)
    monkeypatch.setenv("NETSUITE_TOKEN_SECRET", "ts" * 18)
    monkeypatch.setenv("NETSUITE_LOG_LEVEL", "INFO")
    config = Config.from_env()
    assert config.account == "999_SB1"
    assert config.log_level == "INFO"
    assert isinstance(config.auth, TokenAuth)
    assert config.auth.consumer_key == "ck" * 18


def test_from_env_skips_missing_keys(monkeypatch):
    """Only env vars actually set should be forwarded — missing ones
    must not show up as empty strings or `None`."""
    # Strip any pre-existing NETSUITE_ vars.
    for key in list(__import__("os").environ):
        if key.startswith("NETSUITE_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("NETSUITE_ACCOUNT", "123_SB1")
    monkeypatch.setenv("NETSUITE_USERNAME", "u")
    monkeypatch.setenv("NETSUITE_PASSWORD", "p")
    config = Config.from_env()
    assert config.account == "123_SB1"
    assert isinstance(config.auth, UsernamePasswordAuth)


# ---------------------------------------------------------------------------
# `Config.from_ini`
# ---------------------------------------------------------------------------


def _write_ini(tmp_path, body, name="netsuite.ini"):
    path = tmp_path / name
    path.write_text(dedent(body).lstrip())
    return str(path)


def test_from_ini_default_section(tmp_path):
    path = _write_ini(
        tmp_path,
        """
        [netsuite]
        auth_type = token
        account = 123456
        consumer_key = ck
        consumer_secret = cs
        token_id = ti
        token_secret = ts
        """,
    )
    config = Config.from_ini(path=path)
    assert config.account == "123456"
    assert isinstance(config.auth, TokenAuth)
    assert config.auth.consumer_key == "ck"


def test_from_ini_custom_section(tmp_path):
    path = _write_ini(
        tmp_path,
        """
        [netsuite]
        account = wrong
        consumer_key = w
        consumer_secret = w
        token_id = w
        token_secret = w

        [prod]
        account = 999
        consumer_key = pck
        consumer_secret = pcs
        token_id = pti
        token_secret = pts
        """,
    )
    config = Config.from_ini(path=path, section="prod")
    assert config.account == "999"
    assert config.auth.consumer_key == "pck"


def test_from_ini_rejects_non_token_auth(tmp_path):
    path = _write_ini(
        tmp_path,
        """
        [netsuite]
        auth_type = oauth2
        """,
    )
    with pytest.raises(RuntimeError, match="Only token auth"):
        Config.from_ini(path=path)


def test_from_ini_defaults_auth_type_to_token_when_unspecified(tmp_path):
    path = _write_ini(
        tmp_path,
        """
        [netsuite]
        account = 123
        consumer_key = ck
        consumer_secret = cs
        token_id = ti
        token_secret = ts
        """,
    )
    config = Config.from_ini(path=path)
    assert config.is_token_auth
