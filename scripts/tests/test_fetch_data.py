import pytest
from unittest.mock import MagicMock
from scripts.fetch_data import FECContributionAnalyzer, Contributor

@pytest.fixture
def analyzer():
    """Provides an FECContributionAnalyzer instance with a dummy API key."""
    return FECContributionAnalyzer(api_key="TEST_KEY")

@pytest.fixture
def mock_requests_get(mocker):
    """Mocks the requests.get call."""
    return mocker.patch("requests.get")

# --- Tests for get_contributor_data --- #

def test_get_contributor_data_handles_pagination(analyzer, mock_requests_get):
    """Tests that the function correctly pages through API results."""
    # Mock two pages of results
    mock_requests_get.side_effect = [
        MagicMock(status_code=200, json=lambda: {"results": [{"id": 1}], "pagination": {"pages": 2}}),
        MagicMock(status_code=200, json=lambda: {"results": [{"id": 2}], "pagination": {"pages": 2}}),
    ]
    contributor = Contributor(name="Test Person", employer="Test Corp")
    results = analyzer.get_contributor_data(contributor, "01/01/2024", "01/31/2024")
    assert len(results) == 2
    assert mock_requests_get.call_count == 2

def test_get_contributor_data_handles_api_error(analyzer, mock_requests_get):
    """Tests that the function returns an empty list on API error after retries."""
    mock_requests_get.return_value = MagicMock(status_code=500)
    contributor = Contributor(name="Test Person", employer="Test Corp")
    results = analyzer.get_contributor_data(contributor, "01/01/2024", "01/31/2024")
    assert results == []
    assert mock_requests_get.call_count == 3 # Should retry 3 times

# --- Tests for get_pac_expenditures --- #

def test_get_pac_expenditures_handles_pagination(analyzer, mock_requests_get):
    """Tests that the PAC expenditure function correctly pages through results."""
    mock_requests_get.side_effect = [
        MagicMock(status_code=200, json=lambda: {"results": [{"id": 1}], "pagination": {"pages": 2}}),
        MagicMock(status_code=200, json=lambda: {"results": [{"id": 2}], "pagination": {"pages": 2}}),
    ]
    results = analyzer.get_pac_expenditures(["C123"], "01/01/2024", "01/31/2024")
    assert len(results) == 2
    assert mock_requests_get.call_count == 2

def test_get_pac_expenditures_handles_api_error(analyzer, mock_requests_get):
    """Tests that the PAC expenditure function returns an empty list on API error."""
    mock_requests_get.return_value = MagicMock(status_code=500)
    results = analyzer.get_pac_expenditures(["C123"], "01/01/2024", "01/31/2024")
    assert results == []
    assert mock_requests_get.call_count == 3 # Should retry 3 times
