import asyncio
import time
import httpx
import logging
from unittest.mock import AsyncMock, patch
from helpers.apollo_rate_limiter import apollo_limiter
from enrichment_module.people_enrichment import people_enrichment
from enrichment_module.single_org_enrichment import single_org_enrichment
from enrichment_module.people_search import people_search
from enrichment_module.organization_search import org_search
from enrichment_module.bulk_org_enrichment import bulk_org_enrichment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_unified_rate_limiting():
    # Replace the limiter with a tight one for testing
    import helpers.apollo_rate_limiter
    from aiolimiter import AsyncLimiter
    helpers.apollo_rate_limiter.apollo_limiter = AsyncLimiter(max_rate=2, time_period=2)
    
    # Mock response object
    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "organizations": [], "people": []}
    mock_response.raise_for_status = lambda: None

    async with httpx.AsyncClient() as client:
        # Patch the post method to be an AsyncMock returning our mock_response
        with patch.object(httpx.AsyncClient, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            start_time = time.perf_counter()
            
            # Fire 5 requests across different modules
            tasks = [
                people_enrichment(client, "123", "Test User"),
                single_org_enrichment(client, "example.com"),
                people_search(client, ["org1"], ["domain1"]),
                org_search(client, company_name="Test Co"),
                bulk_org_enrichment(client, ["domain2"])
            ]
            
            await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            logger.info(f"5 requests took {duration:.2f} seconds")
            
            # With 2 req / 2 sec (1 req/sec):
            # Req 1, 2: Instant
            # Req 3: Wait 1 sec
            # Req 4: Wait another 1 sec
            # Req 5: Wait another 1 sec (total 3 sec)
            # So duration should be around 3 seconds
            
            if duration >= 3.0:
                logger.info("VERIFICATION SUCCESS: Rate limiting is unified across modules.")
            else:
                logger.error(f"VERIFICATION FAILURE: Duration {duration:.2f}s is less than expected 3s. Rate limiting might not be unified.")

if __name__ == "__main__":
    asyncio.run(test_unified_rate_limiting())
