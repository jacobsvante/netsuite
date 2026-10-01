"""Tests for `netsuite.json` — the orjson-or-stdlib JSON shim."""

import datetime
import importlib
import sys
from decimal import Decimal
from enum import Enum
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import pytest

from netsuite import json as nsjson

# ---------------------------------------------------------------------------
# Round-trip: dumps→loads should preserve plain dict/list/scalar payloads
# regardless of which JSON backend is in use.
# ---------------------------------------------------------------------------


def test_dumps_loads_round_trips_plain_dict():
    payload = {"a": 1, "b": "two", "c": [1, 2, 3], "d": None, "e": True}
    assert nsjson.loads(nsjson.dumps(payload)) == payload


def test_dumps_returns_str_not_bytes():
    """Even with orjson (which natively returns bytes) we must hand back str."""
    out = nsjson.dumps({"a": 1})
    assert isinstance(out, str)


# ---------------------------------------------------------------------------
# Custom encoders for non-standard types. These only matter for orjson, since
# stdlib json would raise TypeError without `default=` — but the round-trip
# should succeed regardless of which backend is loaded.
# ---------------------------------------------------------------------------


class _Color(Enum):
    RED = "red"
    BLUE = "blue"


@pytest.mark.parametrize(
    "value,expected_decoded",
    [
        (datetime.date(2024, 1, 2), "2024-01-02"),
        (datetime.datetime(2024, 1, 2, 3, 4, 5), "2024-01-02T03:04:05"),
        (datetime.time(3, 4, 5), "03:04:05"),
        (datetime.timedelta(seconds=90), 90.0),
        (Decimal("1.5"), 1.5),
        (_Color.RED, "red"),
        (frozenset([1, 2, 3]), [1, 2, 3]),
        (set([1, 2, 3]), [1, 2, 3]),
        # Encoder serializes Path via str(); expected must match per-OS
        # (POSIX "/tmp/x" vs Windows "\\tmp\\x") rather than hardcode POSIX.
        (Path("/tmp/x"), str(Path("/tmp/x"))),
        (
            UUID("12345678-1234-5678-1234-567812345678"),
            "12345678-1234-5678-1234-567812345678",
        ),
    ],
)
def test_dumps_encodes_supported_types(value, expected_decoded):
    decoded = nsjson.loads(nsjson.dumps({"v": value}))
    if isinstance(expected_decoded, list):
        # set/frozenset have non-deterministic iteration order
        assert sorted(decoded["v"]) == sorted(expected_decoded)
    else:
        assert decoded["v"] == expected_decoded


def test_dumps_bytes_decodes_as_utf8():
    assert nsjson.loads(nsjson.dumps({"v": b"hello"})) == {"v": "hello"}


def test_dumps_str_subclass_is_normalized():
    """orjson rejects str subclasses by default — `_orjson_default` falls
    back to `str(obj)` for them."""

    class StrSub(str):
        pass

    if not nsjson.HAS_ORJSON:
        pytest.skip("Only orjson rejects str subclasses without a default hook")
    assert nsjson.loads(nsjson.dumps({"v": StrSub("x")})) == {"v": "x"}


def test_dumps_unsupported_type_raises():
    """Types with no encoder should raise from `_get_encoder`."""

    class Nope:
        pass

    if not nsjson.HAS_ORJSON:
        pytest.skip(
            "Stdlib json raises TypeError directly without going through _get_encoder"
        )
    with pytest.raises(TypeError, match="Nope"):
        nsjson.dumps({"v": Nope()})


# ---------------------------------------------------------------------------
# Backend selection — exercise the stdlib fallback by reloading the module
# with orjson hidden.
# ---------------------------------------------------------------------------


def test_stdlib_fallback_is_used_when_orjson_unavailable():
    real_orjson = sys.modules.pop("orjson", None)
    try:
        with patch.dict(sys.modules, {"orjson": None}):
            reloaded = importlib.reload(nsjson)
            assert reloaded.HAS_ORJSON is False
            assert reloaded.loads(reloaded.dumps({"a": 1})) == {"a": 1}
    finally:
        if real_orjson is not None:
            sys.modules["orjson"] = real_orjson
        importlib.reload(nsjson)
