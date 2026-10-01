"""Verify NetSuiteSoapApi emits a DeprecationWarning pointing users at
OAuth 2.0. NetSuite is gradually removing SOAP Web Services (2025.2 is the
last planned endpoint), and the warning is the user-facing nudge to migrate."""

import warnings

import pytest

from netsuite import NetSuiteSoapApi
from netsuite.soap_api.client import SOAP_DEPRECATION_MESSAGE
from netsuite.soap_api.zeep import ZEEP_INSTALLED

pytestmark = pytest.mark.skipif(not ZEEP_INSTALLED, reason="Requires zeep")


def test_soap_api_init_emits_deprecation_warning(dummy_config):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        NetSuiteSoapApi(dummy_config)
    deprecation_warnings = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    assert len(deprecation_warnings) == 1
    assert "2025.2" in str(deprecation_warnings[0].message)
    assert "OAuth 2.0" in str(deprecation_warnings[0].message)


def test_soap_deprecation_message_mentions_replacement(dummy_config):
    """The message should point readers at the OAuth2 config class so they
    have a concrete next step, not just a generic warning."""
    assert "OAuth2ClientCredentialsAuth" in SOAP_DEPRECATION_MESSAGE
    assert "REST API" in SOAP_DEPRECATION_MESSAGE
    assert "2025.2" in SOAP_DEPRECATION_MESSAGE
