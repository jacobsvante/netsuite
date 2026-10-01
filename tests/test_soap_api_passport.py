"""Tests for SOAP TokenPassport — signature/nonce/timestamp generation, and
the `make` factory that wraps it for outbound headers."""

import re
from unittest.mock import MagicMock

import pytest

from netsuite.config import Config
from netsuite.soap_api.passport import Passport, TokenPassport
from netsuite.soap_api.passport import make as make_passport
from netsuite.soap_api.zeep import ZEEP_INSTALLED

pytestmark = pytest.mark.skipif(not ZEEP_INSTALLED, reason="Requires zeep")


def _make_passport(config):
    auth = config.auth
    fake_ns = MagicMock()
    return TokenPassport(
        fake_ns,
        account=config.account,
        consumer_key=auth.consumer_key,
        consumer_secret=auth.consumer_secret,
        token_id=auth.token_id,
        token_secret=auth.token_secret,
    )


def test_base_passport_get_element_is_abstract():
    with pytest.raises(NotImplementedError):
        Passport().get_element()


def test_generate_timestamp_is_unix_seconds(dummy_config):
    passport = _make_passport(dummy_config)
    ts = passport._generate_timestamp()
    # Sanity-check: NetSuite's accepted timestamps are seconds since epoch.
    assert ts.isdigit()
    assert int(ts) > 1_500_000_000  # post-2017


def test_generate_nonce_is_digits_with_default_length(dummy_config):
    passport = _make_passport(dummy_config)
    nonce = passport._generate_nonce()
    assert re.fullmatch(r"\d{20}", nonce)


def test_generate_nonce_respects_custom_length(dummy_config):
    passport = _make_passport(dummy_config)
    nonce = passport._generate_nonce(length=8)
    assert re.fullmatch(r"\d{8}", nonce)


def test_signature_message_components(dummy_config):
    passport = _make_passport(dummy_config)
    msg = passport._get_signature_message(nonce="N", timestamp="T")
    assert msg == "&".join(
        [
            dummy_config.account,
            dummy_config.auth.consumer_key,
            dummy_config.auth.token_id,
            "N",
            "T",
        ]
    )


def test_signature_key_combines_secrets(dummy_config):
    passport = _make_passport(dummy_config)
    key = passport._get_signature_key()
    assert (
        key == f"{dummy_config.auth.consumer_secret}&{dummy_config.auth.token_secret}"
    )


def test_signature_value_changes_when_inputs_change(dummy_config):
    passport = _make_passport(dummy_config)
    assert passport._get_signature_value("a", "1") != passport._get_signature_value(
        "a", "2"
    )
    assert passport._get_signature_value("a", "1") != passport._get_signature_value(
        "b", "1"
    )


def test_get_signature_uses_core_token_passport_signature(dummy_config):
    """`_get_signature` should construct a `Core.TokenPassportSignature` with
    the HMAC-SHA256 algorithm marker."""
    passport = _make_passport(dummy_config)
    passport.ns.Core.TokenPassportSignature = MagicMock(return_value="sig-obj")
    result = passport._get_signature(nonce="N", timestamp="T")
    passport.ns.Core.TokenPassportSignature.assert_called_once()
    args, kwargs = passport.ns.Core.TokenPassportSignature.call_args
    assert kwargs == {"algorithm": "HMAC-SHA256"}
    # The first positional is the base64 signature value.
    assert isinstance(args[0], str)
    assert result == "sig-obj"


def test_get_element_returns_token_passport_with_all_fields(dummy_config):
    passport = _make_passport(dummy_config)
    passport.ns.Core.TokenPassportSignature = MagicMock(return_value="sig")
    passport.ns.Core.TokenPassport = MagicMock(return_value="token-passport")
    result = passport.get_element()
    passport.ns.Core.TokenPassport.assert_called_once()
    kwargs = passport.ns.Core.TokenPassport.call_args.kwargs
    assert kwargs["account"] == dummy_config.account
    assert kwargs["consumerKey"] == dummy_config.auth.consumer_key
    assert kwargs["token"] == dummy_config.auth.token_id
    assert kwargs["nonce"].isdigit()
    assert kwargs["timestamp"].isdigit()
    assert kwargs["signature"] == "sig"
    assert result == "token-passport"


def test_make_returns_token_passport_dict_for_token_auth(dummy_config):
    fake_ns = MagicMock()
    fake_ns.Core.TokenPassport.return_value = "tp"
    fake_ns.Core.TokenPassportSignature.return_value = "sig"
    out = make_passport(fake_ns, dummy_config)
    assert "tokenPassport" in out


def test_make_rejects_username_password_auth():
    config = Config(
        account="123456_SB1",
        auth={"username": "u", "password": "p"},
    )
    with pytest.raises(NotImplementedError):
        make_passport(MagicMock(), config)
