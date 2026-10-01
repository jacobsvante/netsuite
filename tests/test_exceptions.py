"""Tests for `netsuite.exceptions` and `netsuite.soap_api.exceptions`."""

import pytest

from netsuite.exceptions import (
    NetsuiteAPIRequestError,
    NetsuiteAPIResponseParsingError,
)
from netsuite.soap_api.exceptions import NetsuiteResponseError


def test_request_error_carries_status_and_text():
    err = NetsuiteAPIRequestError(404, "not found")
    assert err.status_code == 404
    assert err.response_text == "not found"


def test_request_error_str_format():
    err = NetsuiteAPIRequestError(500, "boom")
    assert str(err) == "HTTP500 - boom"


def test_response_parsing_error_subclasses_request_error():
    """Callers catching `NetsuiteAPIRequestError` must also catch parsing
    errors — the latter signals "we got HTTP 2xx but couldn't decode it",
    which is still a request-level failure."""
    err = NetsuiteAPIResponseParsingError(200, "<html>")
    assert isinstance(err, NetsuiteAPIRequestError)
    assert err.status_code == 200
    assert str(err) == "HTTP200 - <html>"


def test_request_error_can_be_raised_and_caught():
    with pytest.raises(NetsuiteAPIRequestError):
        raise NetsuiteAPIRequestError(401, "unauthorized")


def test_soap_response_error_is_an_exception():
    with pytest.raises(NetsuiteResponseError):
        raise NetsuiteResponseError("status detail here")
