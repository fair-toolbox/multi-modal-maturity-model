"""
Tests for BioToolsClient.
"""

import pytest
import requests
from unittest.mock import Mock, patch

from multi_modal_maturity_model.collectors.biotools import BioToolsClient


@pytest.fixture
def collector(self):
    """Create a BioToolsClient instance for testing."""
    return BioToolsClient()


@pytest.fixture
def custom_collector(self):
    """Create a BioToolsClient with custom base URL."""
    return BioToolsClient(base_url="https://custom.bio.tools/api/tool")


@pytest.fixture
def mock_biotools_response(self):
    """Sample bio.tools API response."""
    return {
        "biotoolsID": "blast",
        "biotoolsCURIE": "biotools:blast",
        "name": "BLAST",
        "description": "Basic Local Alignment Search Tool",
        "homepage": "https://blast.ncbi.nlm.nih.gov/",
        "version": ["2.12.0"],
        "topic": [
            {
                "uri": "http://edamontology.org/topic_0080",
                "term": "Sequence analysis",
            }
        ],
        "function": [
            {
                "operation": [
                    {
                        "uri": "http://edamontology.org/operation_0292",
                        "term": "Sequence alignment",
                    }
                ]
            }
        ],
    }


def test_init_default_url(self, collector):
    """Test initialization with default base URL."""
    assert collector.base_url == "https://bio.tools/api/tool"


def test_init_custom_url(self, custom_collector):
    """Test initialization with custom base URL."""
    assert custom_collector.base_url == "https://custom.bio.tools/api/tool"


@patch("multi_modal_maturity_model.collectors.biotools.requests.get")
def test_get_success(self, mock_get, collector, mock_biotools_response):
    """Test successful API call via _get method."""
    mock_response = Mock()
    mock_response.json.return_value = mock_biotools_response
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    result = collector._get("blast")
    # Assertions
    assert result == mock_biotools_response
    mock_get.assert_called_once_with(
        "https://bio.tools/api/tool/blast?format=json", timeout=10
    )
    mock_response.raise_for_status.assert_called_once()


@patch("multi_modal_maturity_model.collectors.biotools.requests.get")
def test_get_http_error(self, mock_get, collector):
    """Test _get method handles HTTP errors."""
    # Setup mock to raise HTTPError
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
    mock_get.return_value = mock_response
    # Call method and expect exception
    with pytest.raises(requests.HTTPError):
        collector._get("nonexistent_tool")


@patch("multi_modal_maturity_model.collectors.biotools.requests.get")
def test_get_timeout(self, mock_get, collector):
    """Test _get method handles timeout errors."""
    # Setup mock to raise Timeout
    mock_get.side_effect = requests.Timeout("Request timed out")
    # Call method and expect exception
    with pytest.raises(requests.Timeout):
        collector._get("blast")
    mock_get.assert_called_once_with(
        "https://bio.tools/api/tool/blast?format=json", timeout=10
    )


@patch("multi_modal_maturity_model.collectors.biotools.requests.get")
def test_get_connection_error(self, mock_get, collector):
    """Test _get method handles connection errors."""
    # Setup mock to raise ConnectionError
    mock_get.side_effect = requests.ConnectionError("Connection failed")
    # Call method and expect exception
    with pytest.raises(requests.ConnectionError):
        collector._get("blast")


@patch("multi_modal_maturity_model.collectors.biotools.requests.get")
def test_get_with_custom_base_url(
    self, mock_get, custom_collector, mock_biotools_response
):
    """Test _get method uses custom base URL."""
    # Setup mock
    mock_response = Mock()
    mock_response.json.return_value = mock_biotools_response
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    # Call method
    result = custom_collector._get("blast")
    # Assertions
    assert result == mock_biotools_response
    mock_get.assert_called_once_with(
        "https://custom.bio.tools/api/tool/blast?format=json", timeout=10
    )


@patch("multi_modal_maturity_model.collectors.biotools.requests.get")
def test_fetch_success(self, mock_get, collector, mock_biotools_response):
    """Test successful fetch method."""
    # Setup mock
    mock_response = Mock()
    mock_response.json.return_value = mock_biotools_response
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    # Call method
    result = collector.fetch("blast")
    # Assertions
    assert result == mock_biotools_response
    mock_get.assert_called_once()


@patch("multi_modal_maturity_model.collectors.biotools.requests.get")
def test_fetch_propagates_exceptions(self, mock_get, collector):
    """Test that fetch method propagates exceptions from _get."""
    # Setup mock to raise exception
    mock_get.side_effect = requests.HTTPError("404 Not Found")
    # Call method and expect exception
    with pytest.raises(requests.HTTPError):
        collector.fetch("nonexistent_tool")


@patch("multi_modal_maturity_model.collectors.biotools.requests.get")
def test_fetch_with_special_characters_in_id(
    self, mock_get, collector, mock_biotools_response
):
    """Test fetch with tool ID containing special characters."""
    # Setup mock
    mock_response = Mock()
    mock_response.json.return_value = mock_biotools_response
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    # Call method with special characters
    result = collector.fetch("tool-name_v2.0")
    # Assertions
    assert result == mock_biotools_response
    mock_get.assert_called_once_with(
        "https://bio.tools/api/tool/tool-name_v2.0?format=json", timeout=10
    )


@patch("multi_modal_maturity_model.collectors.biotools.requests.get")
def test_get_returns_dict(self, mock_get, collector):
    """Test that _get returns a dictionary."""
    # Setup mock with valid JSON
    mock_response = Mock()
    mock_response.json.return_value = {"key": "value"}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    # Call method
    result = collector._get("test_tool")
    # Assertions
    assert isinstance(result, dict)


@patch("multi_modal_maturity_model.collectors.biotools.requests.get")
def test_get_invalid_json(self, mock_get, collector):
    """Test _get method handles invalid JSON response."""
    # Setup mock to raise JSONDecodeError
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError(
        "Invalid JSON", "", 0
    )
    mock_get.return_value = mock_response
    # Call method and expect exception
    with pytest.raises(requests.exceptions.JSONDecodeError):
        collector._get("blast")
