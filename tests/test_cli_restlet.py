"""Tests for the `restlet` CLI command handlers — same approach as the
rest-api handler tests: build the parser, parse argv, invoke `args.func`
with a mocked NetSuite restlet client.
"""

import argparse
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from netsuite.cli import restlet as cli_restlet


def _parser():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    cli_restlet.add_parser(parser, sub)
    return parser


def _mock_netsuite(restlet):
    patcher = patch.object(cli_restlet, "NetSuite")
    ns_cls = patcher.start()
    ns_cls.return_value.restlet = restlet
    return patcher


@pytest.mark.asyncio
async def test_restlet_get(dummy_config):
    args = _parser().parse_args(["restlet", "get", "42", "-d", "3"])
    restlet = MagicMock()
    restlet.get = AsyncMock(return_value={"ok": True})
    patcher = _mock_netsuite(restlet)
    try:
        out = await args.func(dummy_config, args)
    finally:
        patcher.stop()
    restlet.get.assert_awaited_once_with(script_id=42, deploy=3)
    assert out == cli_restlet.json.dumps({"ok": True})


@pytest.mark.parametrize("verb", ["post", "put"])
@pytest.mark.asyncio
async def test_restlet_body_verbs_read_payload(dummy_config, tmp_path, verb):
    payload = tmp_path / "body.json"
    payload.write_text('{"x": 1}')
    args = _parser().parse_args(["restlet", verb, "7", str(payload)])
    restlet = MagicMock()
    setattr(restlet, verb, AsyncMock(return_value={"done": True}))
    patcher = _mock_netsuite(restlet)
    try:
        out = await args.func(dummy_config, args)
    finally:
        patcher.stop()
    method = getattr(restlet, verb)
    method.assert_awaited_once_with(script_id=7, deploy=1, json={"x": 1})
    assert out == cli_restlet.json.dumps({"done": True})


@pytest.mark.asyncio
async def test_restlet_delete_uses_default_deploy(dummy_config):
    # The delete handler currently calls restlet.put (no body) under the hood.
    args = _parser().parse_args(["restlet", "delete", "9"])
    restlet = MagicMock()
    restlet.put = AsyncMock(return_value=None)
    patcher = _mock_netsuite(restlet)
    try:
        out = await args.func(dummy_config, args)
    finally:
        patcher.stop()
    restlet.put.assert_awaited_once_with(script_id=9, deploy=1)
    assert out == cli_restlet.json.dumps(None)


@pytest.mark.asyncio
async def test_restlet_init_runtime_error_calls_parser_error(dummy_config):
    args = _parser().parse_args(["restlet", "get", "1"])
    with patch.object(cli_restlet, "NetSuite") as ns_cls:
        type(ns_cls.return_value).restlet = PropertyMock(
            side_effect=RuntimeError("no restlet config")
        )
        with pytest.raises(SystemExit):
            await args.func(dummy_config, args)
