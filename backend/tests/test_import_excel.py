import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from import_excel.import_excel import get_file_name, return_column_data, create_normalized_data, main

@pytest.fixture
def mock_file():
    file = MagicMock()
    file.filename = "test_fundediq_file.xlsx"
    return file

def test_get_file_name(mock_file):
    assert get_file_name(mock_file) == "test_fundediq_file.xlsx"

def test_return_column_data():
    mock_sheet = MagicMock()
    # Mock iter_rows for headers
    mock_sheet.iter_rows.return_value = [("Company", "Funding Type", "Amount")]
    
    # Mock iter_cols for data
    mock_cell = MagicMock()
    mock_cell.value = "Test Company"
    mock_sheet.iter_cols.return_value = [(MagicMock(value="Header"), mock_cell)]
    
    result = return_column_data(mock_sheet, "Company")
    assert result == ["Test Company"]

@patch("import_excel.import_excel.load_workbook")
@patch("import_excel.import_excel.get_desired_sheet")
def test_create_normalized_data(mock_get_sheet, mock_load_wb, mock_file):
    mock_sheet = MagicMock()
    mock_get_sheet.return_value = mock_sheet
    
    # Mock return_column_data to return some values
    with patch("import_excel.import_excel.return_column_data") as mock_return_col:
        mock_return_col.side_effect = [["Adept"], ["Series A"], ["1M"]]
        
        result = create_normalized_data(mock_file)
        
        assert len(result) == 1
        assert result[0]["company_name"] == ["Adept"]
        assert result[0]["funding_round"] == ["Series A"]
        assert result[0]["amount_raised"] == ["1M"]

@pytest.mark.asyncio
@patch("import_excel.import_excel.create_normalized_data")
@patch("import_excel.import_excel.enrichment_main")
@patch("import_excel.import_excel.get_painpoints_and_service")
@patch("import_excel.import_excel.storage_main")
@patch("import_excel.import_excel.scoring_main")
@patch("import_excel.import_excel.outreach_main")
@patch("asyncpg.create_pool")
async def test_main_flow(
    mock_pool, mock_outreach, mock_scoring, mock_storage, 
    mock_get_ps, mock_enrichment, mock_normalize, mock_file
):
    # Setup mocks
    mock_normalize.return_value = [{"company_name": ["Adept"], "painpoints": [], "service": []}]
    mock_enrichment.return_value = asyncio.Queue()
    mock_get_ps.return_value = [{"company_name": "Adept", "painpoints": ["p1"], "service": "software"}]
    
    # Run main
    await main(mock_file)
    
    # Verify orchestrated calls
    mock_normalize.assert_called_once()
    mock_enrichment.assert_called_once()
    mock_get_ps.assert_called_once()
    mock_storage.assert_called_once()
    mock_scoring.assert_called_once()
    mock_outreach.assert_called_once()
