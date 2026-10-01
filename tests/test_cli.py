"""Tests for the CLI surface — argparse wiring, version/help paths, and
config loading helpers. Does not invoke any real NetSuite calls."""

import argparse
import importlib
from unittest.mock import patch

import pytest

# `netsuite.cli` re-exports the `main` function, shadowing the submodule, so
# import the module object explicitly.
cli_main_module = importlib.import_module("netsuite.cli.main")
from netsuite.cli import helpers, misc  # noqa: E402
from netsuite.cli import rest_api as cli_rest_api  # noqa: E402
from netsuite.cli import restlet, soap_api  # noqa: E402

# ---------------------------------------------------------------------------
# helpers.load_config_or_error
# ---------------------------------------------------------------------------


def test_load_config_or_error_returns_config(tmp_path):
    ini = tmp_path / "ns.ini"
    ini.write_text(
        "[netsuite]\n"
        "account = 999\n"
        "consumer_key = ck\n"
        "consumer_secret = cs\n"
        "token_id = ti\n"
        "token_secret = ts\n"
    )
    parser = argparse.ArgumentParser()
    config = helpers.load_config_or_error(parser, str(ini), "netsuite")
    assert config.account == "999"


def test_load_config_or_error_missing_file_calls_parser_error(tmp_path):
    parser = argparse.ArgumentParser()
    with pytest.raises(SystemExit):
        helpers.load_config_or_error(parser, str(tmp_path / "missing.ini"), "x")


def test_load_config_or_error_missing_section_calls_parser_error(tmp_path):
    ini = tmp_path / "ns.ini"
    ini.write_text(
        "[netsuite]\n"
        "account = 999\n"
        "consumer_key = ck\n"
        "consumer_secret = cs\n"
        "token_id = ti\n"
        "token_secret = ts\n"
    )
    parser = argparse.ArgumentParser()
    with pytest.raises(SystemExit):
        helpers.load_config_or_error(parser, str(ini), "missing-section")


# ---------------------------------------------------------------------------
# misc — version
# ---------------------------------------------------------------------------


def test_misc_version_returns_a_string():
    out = misc.version()
    # Doesn't matter what version exactly — just that it's a non-empty string.
    assert isinstance(out, str) and out


def test_misc_add_parser_registers_version_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    version_parser, _ = misc.add_parser(parser, sub)
    args = parser.parse_args(["version"])
    assert args.func is misc.version


# ---------------------------------------------------------------------------
# Subparser registration — build the full CLI tree without executing it.
# This covers argparse wiring in restlet/rest_api/soap_api.
# ---------------------------------------------------------------------------


def _build_full_parser():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    misc.add_parser(parser, sub)
    restlet.add_parser(parser, sub)
    cli_rest_api.add_parser(parser, sub)
    soap_api.add_parser(parser, sub)
    return parser


def test_full_cli_parser_builds_without_error():
    _build_full_parser()


def test_restlet_get_subcommand_parses_required_args():
    parser = _build_full_parser()
    args = parser.parse_args(["restlet", "get", "42"])
    assert args.script_id == 42
    assert args.deploy == 1  # default


def test_restlet_get_accepts_custom_deploy():
    parser = _build_full_parser()
    args = parser.parse_args(["restlet", "get", "42", "-d", "7"])
    assert args.deploy == 7


def test_restlet_post_requires_payload_file(tmp_path):
    parser = _build_full_parser()
    payload = tmp_path / "payload.json"
    payload.write_text('{"k": "v"}')
    args = parser.parse_args(["restlet", "post", "42", str(payload)])
    assert args.script_id == 42
    # FileType opens the file for reading.
    with args.payload_file as fh:
        assert fh.read() == '{"k": "v"}'


# ---------------------------------------------------------------------------
# main() — the no-argv help path. We avoid actually invoking commands.
# ---------------------------------------------------------------------------


def test_main_with_no_args_prints_help_and_returns(capsys):
    """argparse exits with code 2 when a required subparser is missing.
    `main()` catches the resulting SystemExit-via-Exception in some Python
    versions; in others it bubbles through as SystemExit. Either way the
    process must not raise an unrelated exception."""
    with patch("sys.argv", ["netsuite"]):
        try:
            cli_main_module.main()
        except SystemExit:
            # argparse can call sys.exit on missing required subcommand;
            # that's expected behavior.
            pass


def test_main_handles_version_subcommand(capsys):
    with patch("sys.argv", ["netsuite", "version"]):
        cli_main_module.main()
    captured = capsys.readouterr()
    # `version` was invoked and its return value printed.
    assert captured.out.strip()
