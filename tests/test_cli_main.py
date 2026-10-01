"""Tests for `netsuite.cli.main.main()` — the argv dispatch: per-section help
shortcuts, config loading (env vs ini), and running an async subcommand.
"""

import importlib
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# `netsuite.cli` re-exports the `main` function, shadowing the submodule, so
# import the module object explicitly.
cli_main = importlib.import_module("netsuite.cli.main")
from netsuite.cli import rest_api as cli_rest_api  # noqa: E402


@pytest.mark.parametrize("section", ["rest-api", "soap-api", "restlet"])
def test_section_without_subcommand_prints_help(monkeypatch, section):
    monkeypatch.setattr(sys, "argv", ["netsuite", section])
    # Each branch just prints a help text and returns None.
    assert cli_main.main() is None


def test_run_async_subcommand_via_config_environment(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["netsuite", "--config-environment", "rest-api", "get", "/record/v1/x"],
    )
    api = MagicMock()
    api.get = AsyncMock(return_value={"ok": True})
    ns_cls = MagicMock()
    ns_cls.return_value.rest_api = api
    # from_env supplies the config; log_level drives logging.basicConfig.
    with patch.object(
        cli_main.Config, "from_env", return_value=SimpleNamespace(log_level="INFO")
    ), patch.object(cli_rest_api, "NetSuite", ns_cls):
        cli_main.main()
    api.get.assert_awaited_once()
    out = capsys.readouterr().out
    assert "ok" in out  # the json-encoded response was printed


def test_run_async_subcommand_via_ini_file(monkeypatch, tmp_path, capsys):
    ini = tmp_path / "ns.ini"
    ini.write_text(
        "[netsuite]\n"
        "account = 999\n"
        "consumer_key = ck\n"
        "consumer_secret = cs\n"
        "token_id = ti\n"
        "token_secret = ts\n"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "netsuite",
            "-p",
            str(ini),
            "-c",
            "netsuite",
            "-l",
            "DEBUG",
            "rest-api",
            "get",
            "/record/v1/x",
        ],
    )
    api = MagicMock()
    api.get = AsyncMock(return_value={"items": []})
    ns_cls = MagicMock()
    ns_cls.return_value.rest_api = api
    with patch.object(cli_rest_api, "NetSuite", ns_cls):
        cli_main.main()
    api.get.assert_awaited_once()
    assert "items" in capsys.readouterr().out
