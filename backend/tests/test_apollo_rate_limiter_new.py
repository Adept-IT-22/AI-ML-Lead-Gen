import asyncio
import time
import pytest
from httpx import Response, HTTPStatusError, Request
import logging
import sys
import os

pytestmark = pytest.mark.asyncio

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from helpers.apollo_rate_limiter import rate_limited_apollo_call

# Configure logging to see the retries
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def mock_api_call(attempts_needed=1):
    """A mock API call that fails with 429 until 'attempts_needed' is reached."""
    call_count = 0
    
    async def call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        print(f"Call attempt {call_count}")
        if call_count < attempts_needed:
            # Create a mock 429 response
            request = Request("POST", "https://api.apollo.io/mock")
            response = Response(429, request=request)
            raise HTTPStatusError("Rate limit exceeded", request=request, response=response)
        return {"status": "success", "count": call_count}
    
    return call

async def test_retry_on_429():
    """Verify that the rate limiter retries on 429 errors."""
    print("\n--- Testing Retry on 429 ---")
    mock_call = await mock_api_call(attempts_needed=3)
    
    start_time = time.perf_counter()
    result = await rate_limited_apollo_call(mock_call)
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    print(f"Result: {result}, Duration: {duration:.2f}s")
    
    assert result["status"] == "success"
    assert result["count"] == 3
    # With exponential backoff (min=2), 2 retries should take at least 2s.
    assert duration >= 2
    print("Test passed: Retry on 429 works!")

async def test_rate_limiting_delay():
    """Verify that the rate limiter enforces a delay between calls."""
    print("\n--- Testing Rate Limiting Delay ---")
    async def quick_call():
        return "ok"
    
    start_time = time.perf_counter()
    # Call 1
    await rate_limited_apollo_call(quick_call)
    # Call 2 (should wait ~0.4s)
    await rate_limited_apollo_call(quick_call)
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    print(f"Duration for 2 calls: {duration:.2f}s")
    assert duration >= 0.4
    print("Test passed: Rate limiting delay works!")

async def main():
    try:
        await test_retry_on_429()
        await test_rate_limiting_delay()
        print("\nAll standalone tests passed!")
    except Exception as e:
        print(f"\nTests failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
