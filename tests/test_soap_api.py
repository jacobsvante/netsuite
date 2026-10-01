from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netsuite import NetSuiteSoapApi
from netsuite.config import Config, TokenAuth
from netsuite.soap_api.passport import TokenPassport
from netsuite.soap_api.passport import make as make_passport
from netsuite.soap_api.transports import AsyncNetSuiteTransport
from netsuite.soap_api.zeep import ZEEP_INSTALLED

pytestmark = pytest.mark.skipif(not ZEEP_INSTALLED, reason="Requires zeep")


# ---------------------------------------------------------------------------
# URL / hostname construction
# ---------------------------------------------------------------------------


def test_netsuite_hostname(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config)
    assert soap_api.hostname == "123456-sb1.suitetalk.api.netsuite.com"


def test_netsuite_wsdl_url(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config)
    assert (
        soap_api.wsdl_url
        == "https://123456-sb1.suitetalk.api.netsuite.com/wsdl/v2024_2_0/netsuite.wsdl"
    )


def test_netsuite_wsdl_url_production_account(dummy_config_with_production_account):
    soap_api = NetSuiteSoapApi(dummy_config_with_production_account)
    assert (
        soap_api.wsdl_url
        == "https://123456.suitetalk.api.netsuite.com/wsdl/v2024_2_0/netsuite.wsdl"
    )


def test_netsuite_explicit_version(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config, version="2024.1.0")
    assert soap_api.version == "2024.1.0"
    assert "v2024_1_0" in soap_api.wsdl_url


def test_netsuite_invalid_version_rejected(dummy_config):
    with pytest.raises(AssertionError):
        NetSuiteSoapApi(dummy_config, version="not-a-version")


def test_netsuite_explicit_wsdl_url_overrides_default(dummy_config):
    custom = "https://example.com/custom.wsdl"
    soap_api = NetSuiteSoapApi(dummy_config, wsdl_url=custom)
    assert soap_api.wsdl_url == custom
    assert soap_api.hostname == "example.com"


def test_underscored_version_helpers(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config, version="2024.1.0")
    assert soap_api.underscored_version == "2024_1_0"
    assert soap_api.underscored_version_no_micro == "2024_1"


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


def test_netsuite_transport_initialization(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config)
    soap_api._generate_transport()


def test_transport_fixes_address_to_account_subdomain():
    transport = AsyncNetSuiteTransport(
        "https://123456-sb1.suitetalk.api.netsuite.com/wsdl/v2021_1_0/netsuite.wsdl",
    )
    assert (
        transport._fix_address(
            "https://webservices.netsuite.com/services/NetSuitePort_2021_1"
        )
        == "https://123456-sb1.suitetalk.api.netsuite.com/services/NetSuitePort_2021_1"
    )


# ---------------------------------------------------------------------------
# Cache injection (regression for the docs added in #87 / issue #86)
# ---------------------------------------------------------------------------


def test_default_cache_is_sqlite(dummy_config):
    from zeep.cache import SqliteCache

    soap_api = NetSuiteSoapApi(dummy_config)
    assert isinstance(soap_api.cache, SqliteCache)


def test_custom_cache_is_respected(dummy_config):
    from zeep.cache import InMemoryCache

    cache = InMemoryCache()
    soap_api = NetSuiteSoapApi(dummy_config, cache=cache)
    assert soap_api.cache is cache


# ---------------------------------------------------------------------------
# Passport generation
# ---------------------------------------------------------------------------


def test_token_passport_signature_is_deterministic(dummy_config):
    """Same nonce/timestamp inputs must produce the same signature."""
    soap_api = NetSuiteSoapApi(dummy_config)
    auth = dummy_config.auth
    assert isinstance(auth, TokenAuth)
    passport = TokenPassport(
        soap_api,
        account=dummy_config.account,
        consumer_key=auth.consumer_key,
        consumer_secret=auth.consumer_secret,
        token_id=auth.token_id,
        token_secret=auth.token_secret,
    )
    sig1 = passport._get_signature_value(nonce="123", timestamp="456")
    sig2 = passport._get_signature_value(nonce="123", timestamp="456")
    assert sig1 == sig2
    # And different inputs must produce different signatures.
    assert sig1 != passport._get_signature_value(nonce="123", timestamp="457")


def test_passport_signature_message_format(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config)
    auth = dummy_config.auth
    passport = TokenPassport(
        soap_api,
        account=dummy_config.account,
        consumer_key=auth.consumer_key,
        consumer_secret=auth.consumer_secret,
        token_id=auth.token_id,
        token_secret=auth.token_secret,
    )
    msg = passport._get_signature_message(nonce="N", timestamp="T")
    assert msg.split("&") == [
        dummy_config.account,
        auth.consumer_key,
        auth.token_id,
        "N",
        "T",
    ]


def test_passport_make_rejects_username_password_auth():
    config = Config(
        account="123456_SB1",
        auth={"username": "user", "password": "pass"},
    )
    soap_api = MagicMock()
    with pytest.raises(NotImplementedError):
        make_passport(soap_api, config)


# ---------------------------------------------------------------------------
# Public API: argument shaping (mocking the underlying `request` method)
# ---------------------------------------------------------------------------


def _build_soap_api_with_mocks(config):
    """Return a NetSuiteSoapApi whose `request` and type factories are mocked.

    Bypasses zeep client initialization entirely so we can assert argument
    shaping without a live WSDL connection.
    """

    soap_api = NetSuiteSoapApi(config)
    soap_api.request = AsyncMock(return_value="ok")  # type: ignore[method-assign]

    # Replace each cached_property factory with a MagicMock that records
    # constructor calls. We patch __dict__ to avoid the cached_property
    # descriptor running.
    for name in (
        "Core",
        "Messages",
        "Common",
        "Sales",
        "Relationships",
        "Accounting",
    ):
        soap_api.__dict__[name] = MagicMock(name=name)
    return soap_api


@pytest.mark.asyncio
async def test_get_requires_exactly_one_id(dummy_config):
    soap_api = _build_soap_api_with_mocks(dummy_config)
    # The decorator awaits the inner coroutine, so ValueError is raised when awaited.
    with pytest.raises(ValueError):
        await soap_api.get("customer")
    with pytest.raises(ValueError):
        await soap_api.get("customer", internalId=1, externalId="x")


@pytest.mark.asyncio
async def test_get_with_internal_id_builds_record_ref(dummy_config):
    soap_api = _build_soap_api_with_mocks(dummy_config)
    # The decorator will try to walk `body.readResponse` on the AsyncMock's
    # return value. Bypass by short-circuiting `request` to a non-CompoundValue.
    soap_api.request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    await soap_api.get("customer", internalId=42)
    soap_api.Core.RecordRef.assert_called_once_with(type="customer", internalId=42)
    soap_api.request.assert_awaited_once()
    assert soap_api.request.await_args.args[0] == "get"


@pytest.mark.asyncio
async def test_get_with_external_id_builds_record_ref(dummy_config):
    soap_api = _build_soap_api_with_mocks(dummy_config)
    soap_api.request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    await soap_api.get("customer", externalId="abc")
    soap_api.Core.RecordRef.assert_called_once_with(type="customer", externalId="abc")


@pytest.mark.asyncio
async def test_getList_short_circuits_on_no_ids(dummy_config):
    soap_api = _build_soap_api_with_mocks(dummy_config)
    soap_api.request = AsyncMock()  # type: ignore[method-assign]
    assert await soap_api.getList("customer") == []
    soap_api.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_getList_builds_record_refs_for_each_id(dummy_config):
    soap_api = _build_soap_api_with_mocks(dummy_config)
    soap_api.request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    await soap_api.getList("customer", internalIds=[1, 2], externalIds=["e1"])
    # 2 internal + 1 external = 3 RecordRef constructions
    assert soap_api.Core.RecordRef.call_count == 3
    soap_api.Messages.GetListRequest.assert_called_once()


@pytest.mark.asyncio
async def test_getItemAvailability_short_circuits_on_no_ids(dummy_config):
    soap_api = _build_soap_api_with_mocks(dummy_config)
    soap_api.request = AsyncMock()  # type: ignore[method-assign]
    assert await soap_api.getItemAvailability() == []
    soap_api.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_getItemAvailability_builds_filter_for_ids(dummy_config):
    soap_api = _build_soap_api_with_mocks(dummy_config)
    soap_api.request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    when = datetime(2024, 1, 1, 12, 0, 0)
    await soap_api.getItemAvailability(
        internalIds=[1, 2],
        externalIds=["x"],
        lastQtyAvailableChange=when,
    )
    soap_api.request.assert_awaited_once()
    method, *_ = soap_api.request.await_args.args
    assert method == "getItemAvailability"
    kw = soap_api.request.await_args.kwargs
    item_filters = kw["itemAvailabilityFilter"][0]["item"]["recordRef"]
    assert len(item_filters) == 3
    assert kw["itemAvailabilityFilter"][0]["lastQtyAvailableChange"] == when


@pytest.mark.asyncio
async def test_getAll_passes_record_type(dummy_config):
    soap_api = _build_soap_api_with_mocks(dummy_config)
    soap_api.request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    await soap_api.getAll("subsidiary")
    soap_api.Core.GetAllRecord.assert_called_once_with(recordType="subsidiary")


@pytest.mark.asyncio
async def test_add_update_upsert_pass_record(dummy_config):
    soap_api = _build_soap_api_with_mocks(dummy_config)
    soap_api.request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    record = MagicMock(name="record")
    await soap_api.add(record)
    await soap_api.update(record)
    await soap_api.upsert(record)
    methods = [c.args[0] for c in soap_api.request.await_args_list]
    assert methods == ["add", "update", "upsert"]
    for call in soap_api.request.await_args_list:
        assert call.kwargs["record"] is record


@pytest.mark.asyncio
async def test_search_passes_search_record_and_headers(dummy_config):
    soap_api = _build_soap_api_with_mocks(dummy_config)
    soap_api.request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    record = MagicMock(name="searchRecord")
    headers = {"searchPreferences": MagicMock()}
    await soap_api.search(record=record, additionalHeaders=headers)
    soap_api.request.assert_awaited_once()
    assert soap_api.request.await_args.args[0] == "search"
    assert soap_api.request.await_args.kwargs["searchRecord"] is record
    assert soap_api.request.await_args.kwargs["additionalHeaders"] is headers


@pytest.mark.asyncio
async def test_searchMoreWithId_passes_pagination_args(dummy_config):
    soap_api = _build_soap_api_with_mocks(dummy_config)
    soap_api.request = AsyncMock(return_value=None)  # type: ignore[method-assign]
    await soap_api.searchMoreWithId(searchId="SID", pageIndex=3)
    soap_api.request.assert_awaited_once_with(
        "searchMoreWithId", searchId="SID", pageIndex=3
    )


@pytest.mark.asyncio
async def test_request_attaches_passport_and_extra_headers(dummy_config):
    """`request` must merge the generated passport with `additionalHeaders`."""
    soap_api = NetSuiteSoapApi(dummy_config)
    fake_service = MagicMock()
    fake_method = AsyncMock(return_value="result")
    fake_service.someOp = fake_method
    with patch.object(
        type(soap_api),
        "service",
        new_callable=lambda: property(lambda self: fake_service),
    ), patch.object(soap_api, "generate_passport", return_value={"tokenPassport": "P"}):
        result = await soap_api.request(
            "someOp",
            "arg",
            additionalHeaders={"extra": "X"},
            kw="v",
        )
    assert result == "result"
    fake_method.assert_awaited_once()
    call = fake_method.await_args
    assert call.args == ("arg",)
    assert call.kwargs["kw"] == "v"
    assert call.kwargs["_soapheaders"] == {"tokenPassport": "P", "extra": "X"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_to_builtin_serializes_via_zeep_helpers(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config)
    sentinel = object()
    with patch(
        "netsuite.soap_api.helpers.zeep.helpers.serialize_object",
        return_value=sentinel,
    ) as mock_ser:
        out = soap_api.to_builtin("input")
    assert out is sentinel
    mock_ser.assert_called_once_with("input", target_cls=dict)


def test_with_timeout_uses_transport_settings(dummy_config):
    soap_api = NetSuiteSoapApi(dummy_config)
    fake_settings = MagicMock()
    fake_settings.return_value.__enter__ = MagicMock()
    fake_settings.return_value.__exit__ = MagicMock(return_value=None)
    fake_transport = MagicMock(settings=fake_settings)
    with patch.object(
        type(soap_api),
        "transport",
        new_callable=lambda: property(lambda self: fake_transport),
    ):
        with soap_api.with_timeout(42):
            pass
    fake_settings.assert_called_once_with(timeout=42)


# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------


def test_missing_zeep_raises_runtime_error(dummy_config):
    with patch.object(
        NetSuiteSoapApi, "_has_required_dependencies", return_value=False
    ):
        with pytest.raises(RuntimeError, match="soap_api"):
            NetSuiteSoapApi(dummy_config)
