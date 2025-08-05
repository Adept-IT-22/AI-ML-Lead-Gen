import unittest
import unittest.mock
import httpx
import asyncio
import json
import logging
from lxml import etree, html
from typing import Dict, List, Any
import sys
import os

# Add the parent directory to the path to allow importing modules like utils.data_structures
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from ingestion_module.funding.finsmes.fetch import (
    URL,
    namespace,
    find_newest_sitemap,
    fetch_ai_funding_article_links,
    get_paragraphs,
    extract_paragraphs,
    main as finsmes_main,
    logger # Access the logger from the original module for testing
)

# Mock external dependencies
# Mock the finalize_ai_extraction function
mock_finalize_ai_extraction = unittest.mock.AsyncMock()

# Mock the funding_fetched_data (deepcopy will be called on this)
mock_funding_fetched_data = {
    "type": "funding",
    "article_title": [],
    "article_link": [],
    "article_date": [],
    "company_name": [],
    "company_city": [],
    "company_country": [],
    "company_decision_makers": [],
    "funding_round": [],
    "amount_raised": [],
    "currency": [],
    "investor_companies": [],
    "investor_people": [],
    "tags": [],
    "source": ""
}

# Suppress logging during tests for cleaner output, but keep error logs
logging.disable(logging.CRITICAL)
logger.setLevel(logging.ERROR) # Keep errors for debugging test failures


class TestFinSMEsFetcher(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Reset mocks before each test
        mock_finalize_ai_extraction.reset_mock()
        
        # Mock httpx.AsyncClient
        self.mock_client = unittest.mock.AsyncMock(spec=httpx.AsyncClient)
        
        # Mock aiofiles.open
        self.mock_aiofiles_open = unittest.mock.mock_open()
        
        # Patch the external dependencies
        self.patcher_finalize_ai_extraction = unittest.mock.patch(
            'ingestion_module.funding.finsmes.fetch.finalize_ai_extraction', 
            new=mock_finalize_ai_extraction
        )
        self.patcher_aiofiles_open = unittest.mock.patch(
            'ingestion_module.funding.finsmes.fetch.aiofiles.open', 
            new=self.mock_aiofiles_open
        )
        self.patcher_funding_data_dict = unittest.mock.patch(
            'ingestion_module.funding.finsmes.fetch.funding_fetched_data',
            new=mock_funding_fetched_data
        )

        self.patcher_finalize_ai_extraction.start()
        self.patcher_aiofiles_open.start()
        self.patcher_funding_data_dict.start()

    async def asyncTearDown(self):
        self.patcher_finalize_ai_extraction.stop()
        self.patcher_aiofiles_open.stop()
        self.patcher_funding_data_dict.stop()
        logging.disable(logging.NOTSET) # Re-enable logging after tests

    # --- Helper for mocking HTTP responses ---
    def _mock_response(self, status_code=200, content=b'', headers=None):
        mock_response = unittest.mock.Mock(spec=httpx.Response)
        mock_response.status_code = status_code
        mock_response.content = content
        mock_response.text = content.decode('utf-8')
        mock_response.headers = headers if headers is not None else {}
        mock_response.raise_for_status.return_value = None # Assume success by default
        if status_code >= 400:
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                f"Bad status code: {status_code}", request=httpx.Request("GET", "http://test.com"), response=mock_response
            )
        self.mock_client.get.return_value = mock_response
        return mock_response

    # --- Test find_newest_sitemap ---
    async def test_find_newest_sitemap_success(self):
        sitemap_content = b"""
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>https://www.finsmes.com/wp-sitemap-posts-post-1.xml</loc></sitemap>
            <sitemap><loc>https://www.finsmes.com/wp-sitemap-posts-post-10.xml</loc></sitemap>
            <sitemap><loc>https://www.finsmes.com/wp-sitemap-posts-post-5.xml</loc></sitemap>
            <sitemap><loc>https://www.finsmes.com/wp-sitemap-posts-page-1.xml</loc></sitemap>
        </sitemapindex>
        """
        self._mock_response(content=sitemap_content)
        
        result = await find_newest_sitemap(self.mock_client, URL)
        self.assertEqual(result, "https://www.finsmes.com/wp-sitemap-posts-post-10.xml")
        self.mock_client.get.assert_called_once_with(URL)

    async def test_find_newest_sitemap_no_match(self):
        sitemap_content = b"""
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>https://www.finsmes.com/wp-sitemap-page-1.xml</loc></sitemap>
        </sitemapindex>
        """
        self._mock_response(content=sitemap_content)
        
        result = await find_newest_sitemap(self.mock_client, URL)
        self.assertEqual(result, "") # Should return empty string if no matching sitemap found

    async def test_find_newest_sitemap_http_error(self):
        self._mock_response(status_code=404)
        
        result = await find_newest_sitemap(self.mock_client, URL)
        self.assertIsNone(result) # Should return None on error
        self.mock_client.get.assert_called_once_with(URL)

    # --- Test fetch_ai_funding_article_links ---
    async def test_fetch_ai_funding_article_links_success(self):
        sitemap_content = b"""
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://www.finsmes.com/2025/07/company-ai-raises-funding.html</loc></url>
            <url><loc>https://www.finsmes.com/2025/07/another-company-funding-ai.html</loc></url>
            <url><loc>https://www.finsmes.com/2025/07/not-ai-not-funding.html</loc></url>
            <url><loc>https://www.finsmes.com/2025/07/company-ai-not-funding.html</loc></url>
            <url><loc>https://www.finsmes.com/2025/07/company-funding-not-ai.html</loc></url>
        </urlset>
        """
        self._mock_response(content=sitemap_content)
        
        test_url = "https://www.finsmes.com/wp-sitemap-posts-post-10.xml"
        result = await fetch_ai_funding_article_links(self.mock_client, test_url)
        
        expected_links = [
            "https://www.finsmes.com/2025/07/company-ai-raises-funding.html",
            "https://www.finsmes.com/2025/07/another-company-funding-ai.html"
        ]
        self.assertCountEqual(result, expected_links) # Use assertCountEqual for lists where order doesn't matter
        self.mock_client.get.assert_called_once_with(test_url)

    async def test_fetch_ai_funding_article_links_no_ai_or_funding(self):
        sitemap_content = b"""
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://www.finsmes.com/2025/07/company-tech-news.html</loc></url>
            <url><loc>https://www.finsmes.com/2025/07/another-story.html</loc></url>
        </urlset>
        """
        self._mock_response(content=sitemap_content)
        
        test_url = "https://www.finsmes.com/wp-sitemap-posts-post-10.xml"
        result = await fetch_ai_funding_article_links(self.mock_client, test_url)
        self.assertEqual(result, [])
        self.mock_client.get.assert_called_once_with(test_url)

    async def test_fetch_ai_funding_article_links_http_error(self):
        self._mock_response(status_code=500)
        
        test_url = "https://www.finsmes.com/wp-sitemap-posts-post-10.xml"
        result = await fetch_ai_funding_article_links(self.mock_client, test_url)
        self.assertEqual(result, [])
        self.mock_client.get.assert_called_once_with(test_url)

    # --- Test extract_paragraphs ---
    async def test_extract_paragraphs_success(self):
        article_html = b"""
        <html><body>
            <div class="tdb-block-inner td-fix-index">
                <p>Paragraph 1 with content.</p>
                <p>Another paragraph.</p>
                <p></p> <!-- Empty paragraph, should be ignored -->
                <p>  Whitespace paragraph.  </p>
            </div>
            <p>Outside div paragraph.</p>
        </body></html>
        """
        self._mock_response(content=article_html)
        
        test_url = "http://test.com/article1.html"
        url, paragraphs = await extract_paragraphs(self.mock_client, test_url)
        
        self.assertEqual(url, test_url)
        self.assertEqual(paragraphs, ["Paragraph 1 with content.", "Another paragraph.", "Whitespace paragraph."])
        self.mock_client.get.assert_called_once_with(test_url)

    async def test_extract_paragraphs_no_paragraphs(self):
        article_html = b"""
        <html><body>
            <div class="tdb-block-inner td-fix-index">
                <span>No paragraphs here.</span>
            </div>
        </body></html>
        """
        self._mock_response(content=article_html)
        
        test_url = "http://test.com/article2.html"
        url, paragraphs = await extract_paragraphs(self.mock_client, test_url)
        
        self.assertEqual(url, test_url)
        self.assertEqual(paragraphs, [])
        self.mock_client.get.assert_called_once_with(test_url)

    async def test_extract_paragraphs_http_error(self):
        self._mock_response(status_code=404)
        
        test_url = "http://test.com/article3.html"
        url, paragraphs = await extract_paragraphs(self.mock_client, test_url)
        
        self.assertEqual(url, test_url)
        self.assertEqual(paragraphs, [])
        self.mock_client.get.assert_called_once_with(test_url)

    # --- Test get_paragraphs ---
    async def test_get_paragraphs_success(self):
        # Mock extract_paragraphs to return specific data
        with unittest.mock.patch('ingestion_module.funding.finsmes.fetch.extract_paragraphs') as mock_extract_paragraphs:
            mock_extract_paragraphs.side_effect = [
                ("url1", ["p1a", "p1b"]),
                ("url2", ["p2a"])
            ]
            
            urls = ["url1", "url2"]
            results = await get_paragraphs(self.mock_client, urls)
            
            self.assertEqual(results["urls"], ["url1", "url2"])
            self.assertEqual(results["paragraphs"], ["p1a\np1b", "p2a"])
            self.assertEqual(mock_extract_paragraphs.call_count, 2)

    async def test_get_paragraphs_empty_urls(self):
        results = await get_paragraphs(self.mock_client, [])
        self.assertEqual(results, {"urls": [], "paragraphs": []})

    async def test_get_paragraphs_error_in_extraction(self):
        # Mock extract_paragraphs to raise an exception for one of the calls
        with unittest.mock.patch('ingestion_module.funding.finsmes.fetch.extract_paragraphs') as mock_extract_paragraphs:
            mock_extract_paragraphs.side_effect = [
                ("url1", ["p1a"]),
                Exception("Simulated extraction error"), # Simulate an error for the second URL
                ("url3", ["p3a"])
            ]
            
            urls = ["url1", "url2", "url3"]
            
            # The asyncio.as_completed loop will continue even if one task fails,
            # but the overall get_paragraphs function will catch and log the error.
            # The returned results will only contain successfully processed items.
            results = await get_paragraphs(self.mock_client, urls)
            
            # The exact content of results might vary depending on which tasks complete before the exception is caught,
            # but it should not crash and should contain valid data for successful ones.
            # Since the outer try-except in get_paragraphs catches the exception, it returns {"": [""]}
            # if an exception occurs during the async for loop.
            self.assertEqual(results, {"": [""]}) # Based on the current error handling in get_paragraphs
            self.assertEqual(mock_extract_paragraphs.call_count, 3) # All tasks are still attempted

    # --- Test main function ---
    async def test_main_success_with_data(self):
        # Mock responses for the entire pipeline
        self.mock_client.get.side_effect = [
            self._mock_response(content=b"""
            <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <sitemap><loc>https://www.finsmes.com/wp-sitemap-posts-post-1.xml</loc></sitemap>
            </sitemapindex>
            """),
            self._mock_response(content=b"""
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <url><loc>https://www.finsmes.com/2025/07/company-ai-raises-funding.html</loc></url>
            </urlset>
            """),
            self._mock_response(content=b"""
            <html><body><div class="tdb-block-inner td-fix-index"><p>Test paragraph.</p></div></body></html>
            """)
        ]

        # Mock LLM extraction to return valid data
        mock_finalize_ai_extraction.return_value = {
            "article_title": ["Test Title"],
            "article_link": ["http://test.com/article.html"],
            "article_date": ["2025-07-01"],
            "company_name": ["Test Co"],
            "tags": [["AI", "Funding"]]
        }
        
        # Run the main function
        await finsmes_main()
        
        # Assert that aiofiles.open was called with the correct filename and mode
        self.mock_aiofiles_open.assert_called_once_with("finSMEs_data.txt", "a")
        
        # Assert that data was written to the file
        written_content = self.mock_aiofiles_open().writelines.call_args[0][0]
        written_data = json.loads(written_content)
        
        self.assertEqual(written_data["article_title"], ["Test Title"])
        self.assertEqual(written_data["source"], "FinSMEs")
        self.assertTrue(len(written_data["article_link"]) > 0) # Check if links are populated
        
        # Verify LLM was called
        mock_finalize_ai_extraction.assert_called_once()

    async def test_main_llm_extraction_failure(self):
        # Mock responses for fetching data
        self.mock_client.get.side_effect = [
            self._mock_response(content=b"""<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://www.finsmes.com/wp-sitemap-posts-post-1.xml</loc></sitemap></sitemapindex>"""),
            self._mock_response(content=b"""<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://www.finsmes.com/2025/07/company-ai-raises-funding.html</loc></url></urlset>"""),
            self._mock_response(content=b"""<html><body><div class="tdb-block-inner td-fix-index"><p>Test paragraph.</p></div></body></html>""")
        ]

        # Mock LLM extraction to raise an exception
        mock_finalize_ai_extraction.side_effect = Exception("LLM API error")
        
        # Run the main function
        await finsmes_main()
        
        # Assert that aiofiles.open was NOT called (because extracted_data will be empty)
        self.mock_aiofiles_open.assert_not_called()
        
        # Verify LLM was called
        mock_finalize_ai_extraction.assert_called_once()

    async def test_main_no_ai_urls(self):
        # Mock responses for fetching data, but no AI URLs found
        self.mock_client.get.side_effect = [
            self._mock_response(content=b"""<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://www.finsmes.com/wp-sitemap-posts-post-1.xml</loc></sitemap></sitemapindex>"""),
            self._mock_response(content=b"""<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://www.finsmes.com/2025/07/company-no-ai-no-funding.html</loc></url></urlset>""") # No AI/Funding links
        ]
        
        # Run the main function
        await finsmes_main()
        
        # Assert that aiofiles.open was NOT called (because results["urls"] will be empty)
        self.mock_aiofiles_open.assert_not_called()
        
        # Verify LLM was NOT called
        mock_finalize_ai_extraction.assert_not_called()

    async def test_main_no_sitemap_found(self):
        # Mock sitemap fetch to return empty string (no newest sitemap)
        self.mock_client.get.return_value = self._mock_response(content=b"""
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>https://www.finsmes.com/wp-sitemap-page-1.xml</loc></sitemap>
        </sitemapindex>
        """)
        
        await finsmes_main()
        
        # No further HTTP calls should be made, no LLM call, no file write
        self.assertEqual(self.mock_client.get.call_count, 1) # Only the initial sitemap fetch
        mock_finalize_ai_extraction.assert_not_called()
        self.mock_aiofiles_open.assert_not_called()


# To run the tests, you can use:
# python -m unittest your_test_file_name.py
# Make sure to adjust the import paths if your test file is not in the same directory as finsmes.py