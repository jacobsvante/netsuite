"""Tests for the `rest-api` CLI command handlers.

Each subcommand registers an async `func(config, args)` closure via argparse
defaults. We build the real parser, parse argv, and invoke `args.func` with a
mocked `NetSuite` so the handlers run end-to-end (param assembly, payload-file
reading, header parsing, JSON encoding) without touching the network.
"""

import argparse
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from netsuite.cli import rest_api as cli_rest_api


def _parser():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    cli_rest_api.add_parser(parser, sub)
    return parser


def _mock_netsuite(api):
    """Patch the NetSuite class used by the handlers so `.rest_api` is `api`."""
    patcher = patch.object(cli_rest_api, "NetSuite")
    ns_cls = patcher.start()
    ns_cls.return_value.rest_api = api
    return patcher


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_assembles_all_params_and_headers(dummy_config):
    args = _parser().parse_args(
        [
            "rest-api",
            "get",
            "/record/v1/customer",
            "-l",
            "5",
            "-o",
            "2",
            "-e",
            "-f",
            "id",
            "name",
            "-E",
            "addressBook",
            "-q",
            "lastName START Doe",
            "-H",
            "X-Foo: 1",
        ]
    )
    api = MagicMock()
    api.get = AsyncMock(return_value={"ok": True})
    patcher = _mock_netsuite(api)
    try:
        out = await args.func(dummy_config, args)
    finally:
        patcher.stop()
    assert out == cli_rest_api.json.dumps({"ok": True})
    _, kwargs = api.get.await_args
    assert kwargs["params"] == {
        "expandSubResources": "true",
        "limit": 5,
        "offset": 2,
        "fields": "id,name",
        "expand": "addressBook",
        "q": "lastName START Doe",
    }
    assert kwargs["headers"] == {"X-Foo": "1"}


@pytest.mark.asyncio
async def test_get_with_no_optional_params(dummy_config):
    args = _parser().parse_args(["rest-api", "get", "/record/v1/customer/1"])
    api = MagicMock()
    api.get = AsyncMock(return_value={})
    patcher = _mock_netsuite(api)
    try:
        await args.func(dummy_config, args)
    finally:
        patcher.stop()
    _, kwargs = api.get.await_args
    assert kwargs["params"] == {}
    assert kwargs["headers"] == {}


# ---------------------------------------------------------------------------
# POST / PUT / PATCH (payload-file bodies)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("verb", ["post", "put", "patch"])
@pytest.mark.asyncio
async def test_body_verbs_read_payload_file(dummy_config, tmp_path, verb):
    payload = tmp_path / "body.json"
    payload.write_text('{"companyName": "Acme"}')
    args = _parser().parse_args(
        ["rest-api", verb, "/record/v1/customer", str(payload), "-H", "A: b"]
    )
    api = MagicMock()
    setattr(api, verb, AsyncMock(return_value={"id": "1"}))
    patcher = _mock_netsuite(api)
    try:
        out = await args.func(dummy_config, args)
    finally:
        patcher.stop()
    method = getattr(api, verb)
    _, kwargs = method.await_args
    assert kwargs["json"] == {"companyName": "Acme"}
    assert kwargs["headers"] == {"A": "b"}
    assert out == cli_rest_api.json.dumps({"id": "1"})


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_calls_delete(dummy_config):
    args = _parser().parse_args(["rest-api", "delete", "/record/v1/customer/eid:abc"])
    api = MagicMock()
    api.delete = AsyncMock(return_value=None)
    patcher = _mock_netsuite(api)
    try:
        out = await args.func(dummy_config, args)
    finally:
        patcher.stop()
    args_, _ = api.delete.await_args
    assert args_[0] == "/record/v1/customer/eid:abc"
    assert out == cli_rest_api.json.dumps(None)


# ---------------------------------------------------------------------------
# SuiteQL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suiteql_reads_query_file(dummy_config, tmp_path):
    q = tmp_path / "q.sql"
    q.write_text("SELECT id FROM customer")
    args = _parser().parse_args(["rest-api", "suiteql", str(q), "-l", "50", "-o", "5"])
    api = MagicMock()
    api.suiteql = AsyncMock(return_value={"items": []})
    patcher = _mock_netsuite(api)
    try:
        out = await args.func(dummy_config, args)
    finally:
        patcher.stop()
    _, kwargs = api.suiteql.await_args
    assert kwargs["q"] == "SELECT id FROM customer"
    assert kwargs["limit"] == 50
    assert kwargs["offset"] == 5
    assert out == cli_rest_api.json.dumps({"items": []})


# ---------------------------------------------------------------------------
# jsonschema / openapi
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jsonschema_passes_record_type(dummy_config):
    args = _parser().parse_args(["rest-api", "jsonschema", "salesOrder"])
    api = MagicMock()
    api.jsonschema = AsyncMock(return_value={"type": "object"})
    patcher = _mock_netsuite(api)
    try:
        out = await args.func(dummy_config, args)
    finally:
        patcher.stop()
    api.jsonschema.assert_awaited_once_with("salesOrder")
    assert out == cli_rest_api.json.dumps({"type": "object"})


@pytest.mark.asyncio
async def test_openapi_passes_record_types(dummy_config):
    args = _parser().parse_args(["rest-api", "openapi", "customer", "invoice"])
    api = MagicMock()
    api.openapi = AsyncMock(return_value={"openapi": "3.0"})
    patcher = _mock_netsuite(api)
    try:
        out = await args.func(dummy_config, args)
    finally:
        patcher.stop()
    api.openapi.assert_awaited_once_with(["customer", "invoice"])
    assert out == cli_rest_api.json.dumps({"openapi": "3.0"})


# ---------------------------------------------------------------------------
# openapi-serve (HTTP server mocked out)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openapi_serve_with_record_types(dummy_config):
    args = _parser().parse_args(
        ["rest-api", "openapi-serve", "customer", "-p", "9001", "-b", "0.0.0.0"]
    )
    api = MagicMock()
    api.openapi = AsyncMock(return_value={"openapi": "3.0"})
    patcher = _mock_netsuite(api)
    with patch.object(cli_rest_api.http.server, "test") as serve:
        try:
            await args.func(dummy_config, args)
        finally:
            patcher.stop()
    serve.assert_called_once()
    assert serve.call_args.kwargs["port"] == 9001
    assert serve.call_args.kwargs["bind"] == "0.0.0.0"


@pytest.mark.asyncio
async def test_openapi_serve_without_record_types_warns(dummy_config, caplog):
    args = _parser().parse_args(["rest-api", "openapi-serve"])
    api = MagicMock()
    api.openapi = AsyncMock(return_value={"openapi": "3.0"})
    patcher = _mock_netsuite(api)
    import logging

    with patch.object(cli_rest_api.http.server, "test"):
        with caplog.at_level(logging.WARNING, logger="netsuite"):
            try:
                await args.func(dummy_config, args)
            finally:
                patcher.stop()
    api.openapi.assert_awaited_once_with([])
    assert any("ALL known record types" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Header parsing + error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repeated_header_becomes_list(dummy_config):
    args = _parser().parse_args(
        ["rest-api", "get", "/x", "-H", "X-Multi: 1", "-H", "X-Multi: 2"]
    )
    api = MagicMock()
    api.get = AsyncMock(return_value={})
    patcher = _mock_netsuite(api)
    try:
        await args.func(dummy_config, args)
    finally:
        patcher.stop()
    _, kwargs = api.get.await_args
    assert kwargs["headers"] == {"X-Multi": ["1", "2"]}


@pytest.mark.asyncio
async def test_invalid_header_calls_parser_error(dummy_config):
    args = _parser().parse_args(["rest-api", "get", "/x", "-H", "no-colon-here"])
    api = MagicMock()
    api.get = AsyncMock(return_value={})
    patcher = _mock_netsuite(api)
    try:
        # parser.error raises SystemExit
        with pytest.raises(SystemExit):
            await args.func(dummy_config, args)
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_rest_api_init_runtime_error_calls_parser_error(dummy_config):
    args = _parser().parse_args(["rest-api", "get", "/x"])
    with patch.object(cli_rest_api, "NetSuite") as ns_cls:
        type(ns_cls.return_value).rest_api = PropertyMock(
            side_effect=RuntimeError("missing creds")
        )
        with pytest.raises(SystemExit):
            await args.func(dummy_config, args)
