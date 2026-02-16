import pytest
from normalization_module.hiring_normalization import normalize_hiring_data
from normalization_module.funding_normalization import normalize_funding_data

@pytest.mark.asyncio
async def test_hiring_normalization_preserves_service():
    """Test that service field is preserved during hiring normalization"""
    ingested_data = {
        "source": "hackernews",
        "article_id": ["123"],
        "company_name": ["TechCorp"],
        "title": ["Hiring ML Engineers"],
        "link": ["http://example.com"],
        "article_date": ["2026-01-01"],
        "city": ["SF"],
        "country": ["USA"],
        "company_decision_makers": [[]],
        "company_decision_makers_position": [[]],
        "job_roles": [[]],
        "hiring_reasons": [[]],
        "tags": [[]],
        "painpoints": [[]],
        "service": ["AI/ML"],  # List of strings, one per article
    }
    
    result = await normalize_hiring_data(ingested_data)
    
    # Result is a dictionary with lists, not a list of dictionaries
    assert "service" in result
    assert isinstance(result["service"], list)
    assert len(result["service"]) == 1
    assert result["service"][0] == "AI/ML"  # Normalized (stripped)

@pytest.mark.asyncio
async def test_funding_normalization_preserves_service():
    """Test service field in funding normalization"""
    ingested_data = {
        "source": "techcrunch",
        "article_id": ["456"],
        "company_name": ["StartupXYZ"],
        "title": ["Funding Round"],
        "link": ["http://example.com"],
        "article_date": ["2026-01-01"],
        "city": ["SF"],
        "country": ["USA"],
        "company_decision_makers": [[]],
        "company_decision_makers_position": [[]],
        "funding_round": ["Series A"],
        "amount_raised": ["5M"],
        "currency": ["USD"],
        "investor_companies": [[]],
        "investor_people": [[]],
        "tags": [[]],
        "painpoints": [[]],
        "service": ["Software Development International"],  # List of strings, one per article
    }
    
    result = await normalize_funding_data(ingested_data)
    
    # This test will currently fail because normalize_funding_data doesn't handle service
    assert "service" in result
    assert isinstance(result["service"], list)
    assert len(result["service"]) == 1
    assert result["service"][0] == "Software Development International"