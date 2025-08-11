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
import copy

# Add the parent directory to the path to allow importing modules
# like utils.data_structures and the fetch file itself.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from ingestion_module.funding.techcrunch.fetch import (
    URL,
    traverse_sitemap,
    extract_paragraph,
    get_paragraphs,
    main as techcrunch_main,
    funding_data_dict
)

# Mock external dependencies
# Mock the LLM function
mock_finalize_ai_extraction = unittest.mock.AsyncMock()

# Mock the funding_fetched_data (deepcopy will be called on this)
# A deepcopy of the original is needed for the test's `funding_data_dict`
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

# Suppress logging during tests for cleaner output
logging.disable(logging.CRITICAL)


# In test_techcrunch.py
class TestTechCrunchFetcher(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Reset mocks before each test
        mock_finalize_ai_extraction.reset_mock()
        
        # Mock httpx.AsyncClient
        self.mock_client = unittest.mock.AsyncMock(spec=httpx.AsyncClient)
        
        # Mock aiofiles.open
        self.mock_aiofiles_open = unittest.mock.mock_open()
        
        # Patch the external dependencies. Note the new patches.
        self.patcher_finalize_ai_extraction = unittest.mock.patch(
            'ingestion_module.funding.techcrunch.fetch.finalize_ai_extraction', 
            new=mock_finalize_ai_extraction
        )
        self.patcher_aiofiles_open = unittest.mock.patch(
            'ingestion_module.funding.techcrunch.fetch.aiofiles.open', 
            new=self.mock_aiofiles_open
        )
        self.patcher_funding_data_dict = unittest.mock.patch(
            'ingestion_module.funding.techcrunch.fetch.funding_data_dict', 
            new=mock_funding_fetched_data
        )
        
        # NEW: Patch httpx.AsyncClient. The target is the module where it's used.
        self.patcher_httpx_client = unittest.mock.patch(
            'ingestion_module.funding.techcrunch.fetch.httpx.AsyncClient',
            new=unittest.mock.AsyncMock(return_value=self.mock_client)
        )

        self.patcher_finalize_ai_extraction.start()
        self.patcher_aiofiles_open.start()
        self.patcher_funding_data_dict.start()
        self.patcher_httpx_client.start()

    async def asyncTearDown(self):
        self.patcher_finalize_ai_extraction.stop()
        self.patcher_aiofiles_open.stop()
        self.patcher_funding_data_dict.stop()
        self.patcher_httpx_client.stop() # NEW: Stop the new patcher
        logging.disable(logging.NOTSET)

    # --- Helper for mocking HTTP responses ---
    def _mock_response(self, status_code=200, content=b'', headers=None):
        mock_response = unittest.mock.Mock(spec=httpx.Response)
        mock_response.status_code = status_code
        mock_response.content = content
        mock_response.text = content.decode('utf-8')
        mock_response.headers = headers if headers is not None else {}
        mock_response.raise_for_status.return_value = None
        if status_code >= 400:
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                f"Bad status code: {status_code}", request=httpx.Request("GET", "http://test.com"), response=mock_response
            )
        return mock_response

    # ====================================================================
    # Test traverse_sitemap function
    # ====================================================================

    async def test_traverse_sitemap_success(self):
        sitemap_content = b"""
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
            <url>
                <loc>https://techcrunch.com/2025/08/04/company-ai-raises-funding/</loc>
                <news:news>
                    <news:publication_date>2025-08-04T12:00:00Z</news:publication_date>
                    <news:title>Company AI Raises Funding</news:title>
                </news:news>
            </url>
            <url>
                <loc>https://techcrunch.com/2025/08/04/other-company-tech-raises-funding/</loc>
                <news:news>
                    <news:publication_date>2025-08-04T12:00:00Z</news:publication_date>
                    <news:title>Other Company Tech Raises Funding</news:title>
                </news:news>
            </url>
            <url>
                <loc>https://techcrunch.com/2025/08/03/not-relevant-article/</loc>
                <news:news>
                    <news:publication_date>2025-08-03T12:00:00Z</news:publication_date>
                    <news:title>Not Relevant Article</news:title>
                </news:news>
            </url>
        </urlset>
        """
        self.mock_client.get.return_value = self._mock_response(content=sitemap_content)
        
        result = await traverse_sitemap(self.mock_client, URL)
        
        expected_result = {
            "article_link": ["https://techcrunch.com/2025/08/04/company-ai-raises-funding/"],
            "article_title": ["Company AI Raises Funding"],
            "article_date": ["2025-08-04"]
        }
        self.assertEqual(result, expected_result)
        self.mock_client.get.assert_called_once_with(URL)
    async def test_traverse_sitemap_no_matches(self):
        sitemap_content = b"""
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
            <url>
                <loc>https://techcrunch.com/2025/08/04/company-tech-updates/</loc>
                <news:news>
                    <news:publication_date>2025-08-04T12:00:00Z</news:publication_date>
                    <news:title>Company Tech Updates</news:title>
                </news:news>
            </url>
        </urlset>
        """
        self.mock_client.get.return_value = self._mock_response(content=sitemap_content)
        
        result = await traverse_sitemap(self.mock_client, URL)
        
        expected_result = {
            "article_link": [],
            "article_title": [],
            "article_date": []
        }
        self.assertEqual(result, expected_result)
        self.mock_client.get.assert_called_once_with(URL)

    async def test_traverse_sitemap_http_error(self):
        self.mock_client.get.return_value = self._mock_response(status_code=404)
        
        result = await traverse_sitemap(self.mock_client, URL)
        
        expected_result = {
            "article_link": [],
            "article_title": [],
            "article_date": []
        }
        self.assertEqual(result, expected_result)
        self.mock_client.get.assert_called_once_with(URL)

    # ====================================================================
    # Test extract_paragraph function
    # ====================================================================

    async def test_extract_paragraph_success(self):
        article_html = b"""
        <html><body>
            <div class="article-content">
                <p class="wp-block-paragraph">Paragraph 1 with content.</p>
                <p class="not-a-paragraph">This should be ignored.</p>
                <p class="wp-block-paragraph">Another paragraph.</p>
                <p class="wp-block-paragraph">  Whitespace paragraph.  </p>
                <p class="wp-block-paragraph"></p>
            </div>
        </body></html>
        """
        self.mock_client.get.return_value = self._mock_response(content=article_html)
        
        test_url = "http://test.com/article1.html"
        url, paragraphs = await extract_paragraph(self.mock_client, test_url)
        
        self.assertEqual(url, test_url)
        self.assertEqual(paragraphs, ["Paragraph 1 with content.", "Another paragraph.", "Whitespace paragraph."])
        self.mock_client.get.assert_called_once_with(test_url)

    async def test_extract_paragraph_no_paragraphs(self):
        article_html = b"""
        <html><body>
            <div class="article-content">
                <span>No paragraphs here.</span>
            </div>
        </body></html>
        """
        self.mock_client.get.return_value = self._mock_response(content=article_html)
        
        test_url = "http://test.com/article2.html"
        url, paragraphs = await extract_paragraph(self.mock_client, test_url)
        
        self.assertEqual(url, test_url)
        self.assertEqual(paragraphs, [])
        self.mock_client.get.assert_called_once_with(test_url)

    async def test_extract_paragraph_http_error(self):
        self.mock_client.get.return_value = self._mock_response(status_code=404)
        
        test_url = "http://test.com/article3.html"
        url, paragraphs = await extract_paragraph(self.mock_client, test_url)
        
        self.assertEqual(url, test_url)
        self.assertEqual(paragraphs, [])
        self.mock_client.get.assert_called_once_with(test_url)

    # ====================================================================
    # Test get_paragraphs function
    # ====================================================================

    async def test_get_paragraphs_success(self):
        # Mock extract_paragraph to return specific data
        with unittest.mock.patch('ingestion_module.funding.techcrunch.fetch.extract_paragraph') as mock_extract_paragraph:
            mock_extract_paragraph.side_effect = [
                ("url1", ["p1a", "p1b"]),
                ("url2", ["p2a"])
            ]
            
            urls = ["url1", "url2"]
            results = await get_paragraphs(self.mock_client, urls)
            
            self.assertEqual(results["urls"], ["url1", "url2"])
            self.assertCountEqual(results["paragraphs"], ["p1a\np1b", "p2a"])
            self.assertEqual(mock_extract_paragraph.call_count, 2)

    async def test_get_paragraphs_empty_urls(self):
        results = await get_paragraphs(self.mock_client, [])
        self.assertEqual(results, {"urls": [], "paragraphs": []})
    
    # ====================================================================
    # Test main function (end-to-end scenarios)
    # ====================================================================

    async def test_main_success_with_data(self):
        # Mock responses for the entire pipeline
        self.mock_client.get.side_effect = [
            # 1. Response for traverse_sitemap
            self._mock_response(content=b"""
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
                <url>
                    <loc>https://techcrunch.com/2025/08/04/company-ai-raises-funding/</loc>
                    <news:news>
                        <news:publication_date>2025-08-04T12:00:00Z</news:publication_date>
                        <news:title>Company AI Raises Funding</news:title>
                    </news:news>
                </url>
            </urlset>"""),
            # 2. Response for extract_paragraph call
            self._mock_response(content=b"""
            <html><body><p class="wp-block-paragraph">Test paragraph.</p></body></html>
            """)
        ]

        # Mock LLM extraction to return valid data
        mock_finalize_ai_extraction.return_value = {
            "article_title": ["Test Title"],
            "article_link": ["https://techcrunch.com/2025/08/04/company-ai-raises-funding/"],
            "article_date": ["2025-08-04"],
            "company_name": ["Test Co"],
            "tags": [["AI", "Funding"]]
        }
        
        # Run the main function
        await techcrunch_main()
        
        # Assert that aiofiles.open was called with the correct filename and mode
        self.mock_aiofiles_open.assert_called_once_with("techcrunch_data.txt", "a")
        
        # Assert that data was written to the file
        written_content = self.mock_aiofiles_open().writelines.call_args[0][0]
        written_data = json.loads(written_content)
        
        self.assertEqual(written_data["article_title"], ["Test Title"])
        self.assertEqual(written_data["source"], "TechCrunch")
        self.assertEqual(written_data["article_link"], ["https://techcrunch.com/2025/08/04/company-ai-raises-funding/"])
        
        # Verify LLM was called
        mock_finalize_ai_extraction.assert_called_once()
        
        self.assertEqual(self.mock_client.get.call_count, 2)

    async def test_main_no_ai_urls(self):
        # Mock responses for fetching data, but no AI URLs found
        self.mock_client.get.return_value = self._mock_response(content=b"""
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
            <url>
                <loc>https://techcrunch.com/2025/08/04/company-no-ai-no-funding/</loc>
                <news:news>
                    <news:publication_date>2025-08-04T12:00:00Z</news:publication_date>
                    <news:title>Company No AI No Funding</news:title>
                </news:news>
            </url>
        </urlset>""")
        
        # Run the main function
        await techcrunch_main()
        
        # Assert that aiofiles.open was NOT called
        self.mock_aiofiles_open.assert_not_called()
        
        # Verify LLM was NOT called
        mock_finalize_ai_extraction.assert_not_called()
        
        # Only the initial sitemap fetch should have happened
        self.assertEqual(self.mock_client.get.call_count, 1)
        
    async def test_main_llm_extraction_failure(self):
        # Mock responses for fetching data
        self.mock_client.get.side_effect = [
            self._mock_response(content=b"""<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"><url><loc>https://techcrunch.com/2025/08/04/company-ai-raises-funding/</loc><news:news><news:publication_date>2025-08-04T12:00:00Z</news:publication_date><news:title>Company AI Raises Funding</news:title></news:news></url></urlset>"""),
            self._mock_response(content=b"""<html><body><p class="wp-block-paragraph">Test paragraph.</p></body></html>""")
        ]

        # Mock LLM extraction to raise an exception
        mock_finalize_ai_extraction.side_effect = Exception("LLM API error")
        
        # Run the main function
        await techcrunch_main()
        
        # Assert that aiofiles.open was NOT called (because extracted_data will be empty)
        self.mock_aiofiles_open.assert_not_called()
        
        # Verify LLM was called
        mock_finalize_ai_extraction.assert_called_once()
        
        # All HTTP requests should still have happened
        self.assertEqual(self.mock_client.get.call_count, 2)