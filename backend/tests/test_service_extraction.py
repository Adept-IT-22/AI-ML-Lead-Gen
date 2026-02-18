import pytest
from utils.prompts.hiring_prompt import get_hiring_extraction_prompt
from utils.prompts.funding_prompt import get_funding_extraction_prompt

def test_hiring_service_extraction_ai_ml():
    """Test that AI/ML roles are correctly categorized"""
    article = """
    TechCorp is hiring 5 Machine Learning Engineers and 3 Data Scientists
    to build their new AI recommendation system.
    """
    
    prompt = get_hiring_extraction_prompt(article)
    
    assert "AI/ML" in prompt
    assert "Machine Learning Engineers" in prompt
    assert "Data Scientists" in prompt
    assert '"service"' in prompt # Check if service field instruction is present

def test_hiring_service_extraction_software_dev():
    """Test that software dev roles are correctly categorized"""
    article = """
    StartupXYZ is looking for 10 Full-Stack Engineers and 5 DevOps Engineers
    to scale their SaaS platform.
    """
    
    prompt = get_hiring_extraction_prompt(article)
    
    assert "Software Development International" in prompt
    assert "Full-Stack Engineers" in prompt
    assert '"service"' in prompt

def test_funding_service_extraction():
    """Test service extraction from funding articles"""
    article = """
    AI Startup raises $10M to build machine learning platform for healthcare.
    """
    
    prompt = get_funding_extraction_prompt(article)
    
    assert "AI/ML" in prompt
    assert "Software Development International" in prompt
    assert '"service"' in prompt # Check if service field instruction is present
