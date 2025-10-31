import pytest
from unittest.mock import MagicMock, patch
from scripts.fetch_data import FECContributionAnalyzer, Contributor, main

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

# --- Tests for main --- #

@patch("scripts.fetch_data.FECContributionAnalyzer")
@patch("scripts.fetch_data.os.getenv")
@patch("scripts.fetch_data.open")
@patch("scripts.fetch_data.json.dump")
def test_main_deduplicates_contributions(mock_json_dump, mock_open, mock_getenv, MockAnalyzer):
    """Tests that the main function correctly deduplicates contributions."""
    # Arrange
    mock_getenv.return_value = "TEST_KEY"
    
    # Mock the analyzer to return duplicate contributions
    mock_analyzer_instance = MockAnalyzer.return_value
    mock_analyzer_instance.get_contributor_data.return_value = [
        {"transaction_id": "A", "contributor_name": "John Doe"},
        {"transaction_id": "B", "contributor_name": "Jane Smith"},
        {"transaction_id": "A", "contributor_name": "John Doe"} # Duplicate
    ]
    mock_analyzer_instance.get_pac_expenditures.return_value = []

    # Act
    main()

    # Assert
    # Check that the data written to the file is deduplicated
    assert mock_json_dump.call_count == 2
    written_data = mock_json_dump.call_args_list[0][0][0]
    assert len(written_data) == 2
    assert written_data[0]["transaction_id"] == "A"
    assert written_data[1]["transaction_id"] == "B"
