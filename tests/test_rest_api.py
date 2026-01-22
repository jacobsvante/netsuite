import pytest
from unittest.mock import AsyncMock, Mock
import httpx

from netsuite import NetSuiteRestApi


def test_expected_hostname(dummy_config):
    rest_api = NetSuiteRestApi(dummy_config)
    assert rest_api.hostname == "123456-sb1.suitetalk.api.netsuite.com"


@pytest.mark.asyncio
async def test_post_returns_record_id_from_location_header(dummy_config):
    """Test that POST requests return the record ID extracted from Location header"""
    rest_api = NetSuiteRestApi(dummy_config)
    
    # Mock the response with 204 status and Location header
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_response.headers = {
        "location": "https://123456-sb1.suitetalk.api.netsuite.com/services/rest/record/v1/customer/647"
    }
    mock_response.text = ""
    
    # Mock the _request_impl method to return our mock response
    rest_api._request_impl = AsyncMock(return_value=mock_response)
    
    # Test the post method
    result = await rest_api.post("/record/v1/customer", json={"entityid": "Test Customer"})
    
    # Should return the extracted ID as an integer
    assert result == 647
    assert isinstance(result, int)


@pytest.mark.asyncio
async def test_post_returns_external_id_from_location_header(dummy_config):
    """Test that POST requests return external IDs as strings when they're not numeric"""
    rest_api = NetSuiteRestApi(dummy_config)
    
    # Mock the response with 204 status and Location header containing external ID
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_response.headers = {
        "location": "https://123456-sb1.suitetalk.api.netsuite.com/services/rest/record/v1/customer/eid:CUST001"
    }
    mock_response.text = ""
    
    rest_api._request_impl = AsyncMock(return_value=mock_response)
    
    result = await rest_api.post("/record/v1/customer", json={"entityid": "Test Customer"})
    
    # Should return the external ID as a string
    assert result == "eid:CUST001"
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_create_record_convenience_method(dummy_config):
    """Test the create_record convenience method"""
    rest_api = NetSuiteRestApi(dummy_config)
    
    # Mock the response
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_response.headers = {
        "location": "https://123456-sb1.suitetalk.api.netsuite.com/services/rest/record/v1/customer/123"
    }
    mock_response.text = ""
    
    rest_api._request_impl = AsyncMock(return_value=mock_response)
    
    customer_data = {
        "entityid": "New Customer",
        "companyname": "My Company",
        "subsidiary": {"id": "1"}
    }
    
    result = await rest_api.create_record("customer", customer_data)
    
    # Should return the extracted ID
    assert result == 123
    
    # Verify the correct endpoint was called
    rest_api._request_impl.assert_called_once()
    call_args = rest_api._request_impl.call_args
    assert call_args[0][0] == "POST"  # method
    assert call_args[0][1] == "/record/v1/customer"  # subpath


@pytest.mark.asyncio
async def test_post_without_location_header_returns_none(dummy_config):
    """Test that POST requests return None when there's no Location header"""
    rest_api = NetSuiteRestApi(dummy_config)
    
    # Mock the response with 204 status but no Location header
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_response.headers = {}
    mock_response.text = ""
    
    rest_api._request_impl = AsyncMock(return_value=mock_response)
    
    result = await rest_api.post("/some/other/endpoint", json={"data": "test"})
    
    # Should return None when no Location header is present
    assert result is None


@pytest.mark.asyncio
async def test_get_request_unaffected_by_changes(dummy_config):
    """Test that non-POST requests are unaffected by the Location header logic"""
    rest_api = NetSuiteRestApi(dummy_config)
    
    # Mock the response with 200 status and JSON content
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = '{"id": 123, "entityid": "Test Customer"}'
    mock_response.headers = {
        "location": "https://123456-sb1.suitetalk.api.netsuite.com/services/rest/record/v1/customer/647"
    }
    
    rest_api._request_impl = AsyncMock(return_value=mock_response)
    
    result = await rest_api.get("/record/v1/customer/123")
    
    # Should return the parsed JSON, not the location header
    assert result == {"id": 123, "entityid": "Test Customer"}
