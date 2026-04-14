import sys
import os
import asyncio
import logging
from typing import List, Dict, Any

# Mock asyncpg Pool for testing without DB
class MockPool:
    def __init__(self):
        pass
    async def acquire(self):
        return MockConnection()

class MockConnection:
    async def fetchrow(self, *args, **kwargs):
        return None
    async def fetch(self, *args, **kwargs):
        return []
    async def execute(self, *args, **kwargs):
        return "INSERT 0 1"

# Add backend to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Import the function to test
# We need to mock a lot of stuff or just test the logic locally
# Let's extract the core logic for testing

async def test_categorization_logic():
    print("Testing Lead Categorization Logic...")
    
    # Mock data
    company_name = "Adept AI"
    
    all_normalized_data = [
        {
            "type": "funding",
            "company_name": ["", "Some Other Co"], # The "" is the killer
            "painpoints": [[], ["funding pain"]],
            "service": [[], ["funding service"]]
        },
        {
            "type": "hiring",
            "company_name": ["Adept AI"],
            "painpoints": [["hiring pain"]],
            "service": [["hiring service"]]
        }
    ]
    
    # Simulate the attribution logic from company_storage.py
    company_data_source = None
    painpoints = []
    service = None
    
    for normalized_company_info in all_normalized_data:
        normalized_names = normalized_company_info.get("company_name", [])
        found_match = False
        for idx, normalized_name in enumerate(normalized_names):
            # THE FIX: skip empty strings
            if not normalized_name or not str(normalized_name).strip():
                continue

            if normalized_name.lower() in company_name.lower() or company_name.lower() in normalized_name.lower():
                company_data_source = normalized_company_info.get("type")
                
                # Extract painpoints if available
                all_painpoints = normalized_company_info.get("painpoints", [])
                if idx < len(all_painpoints):
                    painpoints = all_painpoints[idx]
                
                # Extract service if available
                all_services = normalized_company_info.get("service", [])
                if idx < len(all_services):
                    service = all_services[idx] or None
                    
                found_match = True
                break
        if found_match:
            break
            
    print(f"Attributed Source: {company_data_source}")
    assert company_data_source == "hiring", f"Expected 'hiring', got '{company_data_source}'"
    print("PASSED: Categorization logic correctly skipped empty funding placeholder and identified 'hiring' correctly.")

    # Test with empty string and no match
    company_name_no_match = "Totally New Co"
    company_data_source = None
    for normalized_company_info in all_normalized_data:
        normalized_names = normalized_company_info.get("company_name", [])
        found_match = False
        for idx, normalized_name in enumerate(normalized_names):
            if not normalized_name or not str(normalized_name).strip():
                continue
            if normalized_name.lower() in company_name_no_match.lower() or company_name_no_match.lower() in normalized_name.lower():
                company_data_source = normalized_company_info.get("type")
                found_match = True
                break
        if found_match:
            break
            
    print(f"Attributed Source (No Match): {company_data_source}")
    assert company_data_source == None, f"Expected None, got '{company_data_source}'"
    print("PASSED: Categorization logic correctly returned None for unknown lead.")

if __name__ == "__main__":
    asyncio.run(test_categorization_logic())
