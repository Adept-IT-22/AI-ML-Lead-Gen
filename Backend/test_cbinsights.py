import asyncio
import logging
import json
from ingestion_module.funding.cbinsights.fetch import main as cbinsights_main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_cbinsights():
    logger.info("=" * 50)
    logger.info("TESTING CB INSIGHTS MODULE")
    logger.info("=" * 50)
    
    try:
        result = await cbinsights_main()
        
        if result:
            logger.info("\n" + "=" * 50)
            logger.info("RESULTS:")
            logger.info("=" * 50)
            logger.info(f"Type: {result.get('type')}")
            logger.info(f"Source: {result.get('source')}")
            logger.info(f"Number of companies found: {len(result.get('company_name', []))}")
            logger.info(f"Number of links: {len(result.get('link', []))}")
            
            # Print first company details if available
            if result.get('company_name'):
                logger.info("\n" + "-" * 50)
                logger.info("FIRST COMPANY EXAMPLE:")
                logger.info("-" * 50)
                logger.info(f"Company: {result.get('company_name')[0]}")
                logger.info(f"Link: {result.get('link')[0] if result.get('link') else 'N/A'}")
                logger.info(f"Funding Round: {result.get('funding_round')[0] if result.get('funding_round') else 'N/A'}")
                logger.info(f"Amount: {result.get('amount_raised')[0] if result.get('amount_raised') else 'N/A'}")
                logger.info(f"Decision Makers: {result.get('company_decision_makers')[0] if result.get('company_decision_makers') else 'N/A'}")
            
            # Save full result to file for inspection
            with open('cbinsights_test_result.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            logger.info("\n✅ Full results saved to 'cbinsights_test_result.json'")
            
        else:
            logger.warning("❌ No results returned from CB Insights module")
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_cbinsights())

