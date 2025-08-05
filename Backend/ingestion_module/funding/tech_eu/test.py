import unittest
import unittest.mock
import httpx
import asyncio
import json
import logging
import aiofiles
import copy
from lxml import etree, html
from typing import Dict, List, Any

# Adjust path to allow imports from parent directories
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import the functions and variables from the original tech_eu fetch file
from ingestion_module.ai_extraction.extract_funding_content import finalize_ai_extraction
from ingestion_module.funding.tech_eu.fetch import (
    URL,
    fetch_tech_eu_data,
    extract_paragraphs,
    main as tech_eu_main,
    funding_data_dict
)

# Mock external dependencies
mock_finalize_ai_extraction = unittest.mock.AsyncMock()

# Mock the funding_data_dict structure
mock_funding_data_dict = {
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


class TestTechEUFetcher(unittest.IsolatedAsyncioTestCase):
    """
    Unit tests for the Tech.EU fetching and processing module.
    """

    async def asyncSetUp(self):
        """
        Set up mocks and patches before each individual test method runs.
        """
        mock_finalize_ai_extraction.reset_mock()
        
        # Create a mock instance that will represent the `httpx.AsyncClient`
        # inside the `async with` block. This instance will handle `.get()` calls.
        self.mock_client_instance_for_get_calls = unittest.mock.AsyncMock(spec=httpx.AsyncClient)
        
        # Create a MagicMock that will replace the `httpx.AsyncClient` class itself.
        # This mock needs to return an async context manager when called.
        mock_httpx_client_class_for_patch = unittest.mock.MagicMock()
        
        # Configure the `__aenter__` method of the object returned by `httpx.AsyncClient()`.
        # This is the crucial part: when `async with (mock of httpx.AsyncClient() as client)` is run,
        # the `__aenter__` of the *returned object* is called. We want it to return `self.mock_client_instance_for_get_calls`.
        mock_httpx_client_class_for_patch.return_value.__aenter__.return_value = self.mock_client_instance_for_get_calls
        # Also configure __aexit__ for completeness
        mock_httpx_client_class_for_patch.return_value.__aexit__.return_value = None

        # Mock aiofiles.open
        self.mock_aiofiles_open = unittest.mock.mock_open()
        
        # Patch the external dependencies
        self.patcher_finalize_ai_extraction = unittest.mock.patch(
            'ingestion_module.funding.tech_eu.fetch.finalize_ai_extraction', 
            new=mock_finalize_ai_extraction
        )
        self.patcher_aiofiles_open = unittest.mock.patch(
            'ingestion_module.funding.tech_eu.fetch.aiofiles.open', 
            new=self.mock_aiofiles_open
        )
        self.patcher_funding_data_dict = unittest.mock.patch(
            'ingestion_module.funding.tech_eu.fetch.funding_data_dict',
            new=mock_funding_data_dict
        )
        # Patch httpx.AsyncClient (the class) with our configured MagicMock.
        self.patcher_httpx_client_class = unittest.mock.patch(
            'ingestion_module.funding.tech_eu.fetch.httpx.AsyncClient',
            new=mock_httpx_client_class_for_patch
        )

        self.patcher_finalize_ai_extraction.start()
        self.patcher_aiofiles_open.start()
        self.patcher_funding_data_dict.start()
        self.patcher_httpx_client_class.start()

    async def asyncTearDown(self):
        """
        Clean up after each test method by stopping all active patchers.
        """
        self.patcher_finalize_ai_extraction.stop()
        self.patcher_aiofiles_open.stop()
        self.patcher_funding_data_dict.stop()
        self.patcher_httpx_client_class.stop()
        logging.disable(logging.NOTSET)

    def _mock_response(self, status_code=200, content=b'', headers=None):
        """
        Helper method to create a mock httpx.Response object.
        """
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
    # Test fetch_tech_eu_data function
    # ====================================================================

    async def test_fetch_tech_eu_data_success(self):
        """
        Test that fetch_tech_eu_data successfully fetches and filters AI funding links
        and then extracts paragraphs from them.
        """
        sitemap_content = b"""
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
            <url>
                <loc>https://tech.eu/2024/01/ai-startup-raises-seed-funding/</loc>
                <news:news><news:publication_date>2024-01-01T00:00:00Z</news:publication_date></news:news>
            </url>
            <url>
                <loc>https://tech.eu/2024/01/another-tech-company-raises-capital/</loc>
                <news:news><news:publication_date>2024-01-02T00:00:00Z</news:publication_date></news:news>
            </url>
            <url>
                <loc>https://tech.eu/2024/01/company-raises-ai-round-of-funding/</loc>
                <news:news><news:publication_date>2024-01-03T00:00:00Z</news:publication_date></news:news>
            </url>
            <url>
                <loc>https://tech.eu/2024/01/ai-in-healthcare-innovation/</loc>
                <news:news><news:publication_date>2024-01-04T00:00:00Z</news:publication_date></news:news>
            </url>
        </urlset>
        """
        article_html_content_1 = b"""
        <html><body><div class="single-post-content"><p>AI startup raised $5M.</p><p>More details here.</p></div></body></html>
        """
        article_html_content_2 = b"""
        <html><body><div class="single-post-content"><p>Company secured AI funding.</p></div></body></html>
        """

        # Configure side_effect for mock_client_instance_for_get_calls.get
        # First call is for the sitemap, subsequent calls are for article links
        self.mock_client_instance_for_get_calls.get.side_effect = [
            self._mock_response(content=sitemap_content),
            self._mock_response(content=article_html_content_1), # For "ai-startup-raises-seed-funding"
            self._mock_response(content=article_html_content_2)  # For "company-raises-ai-round-of-funding"
        ]
        
        # No need to patch extract_paragraphs here if we want to test its interaction
        # with the mocked client.get. The real extract_paragraphs will be called.

        result = await fetch_tech_eu_data()
        
        expected_urls = [
            "https://tech.eu/2024/01/ai-startup-raises-seed-funding/",
            "https://tech.eu/2024/01/company-raises-ai-round-of-funding/"
        ]
        expected_paragraphs = [
            "AI startup raised $5M.\nMore details here.",
            "Company secured AI funding."
        ]

        self.assertCountEqual(result["urls"], expected_urls)
        self.assertCountEqual(result["paragraphs"], expected_paragraphs)
        # Verify total calls: 1 for sitemap + 2 for filtered articles (via real extract_paragraphs) = 3
        self.assertEqual(self.mock_client_instance_for_get_calls.get.call_count, 3)


    async def test_fetch_tech_eu_data_no_ai_funding_links(self):
        """
        Test fetch_tech_eu_data when the sitemap contains no relevant AI funding links.
        """
        sitemap_content = b"""
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
            <url>
                <loc>https://tech.eu/2024/01/general-tech-news/</loc>
                <news:news><news:publication_date>2024-01-01T00:00:00Z</news:publication_date></news:news>
            </url>
            <url>
                <loc>https://tech.eu/2024/01/ai-innovation-summit/</loc>
                <news:news><news:publication_date>2024-01-02T00:00:00Z</news:publication_date></news:news>
            </url>
        </urlset>
        """
        self.mock_client_instance_for_get_calls.get.return_value = self._mock_response(content=sitemap_content)
        
        # Patch extract_paragraphs here to ensure it's not called if no links are found
        with unittest.mock.patch('ingestion_module.funding.tech_eu.fetch.extract_paragraphs') as mock_extract_paragraphs:
            result = await fetch_tech_eu_data()
            
            self.assertEqual(result, {"urls": [], "paragraphs": []})
            self.mock_client_instance_for_get_calls.get.assert_called_once_with(URL) # Only sitemap fetched
            mock_extract_paragraphs.assert_not_called() # No articles to extract from

    async def test_fetch_tech_eu_data_http_error_sitemap(self):
        """
        Test fetch_tech_eu_data when fetching the sitemap results in an HTTP error.
        """
        self.mock_client_instance_for_get_calls.get.return_value = self._mock_response(status_code=500)
        
        with unittest.mock.patch('ingestion_module.funding.tech_eu.fetch.logger.exception') as mock_logger_exception: # <-- Changed here
            result = await fetch_tech_eu_data()
            
            self.assertEqual(result, {"urls": [], "paragraphs": []})
            self.mock_client_instance_for_get_calls.get.assert_called_once_with(URL)
            mock_logger_exception.assert_called_once() # Verify error logging

    async def test_fetch_tech_eu_data_malformed_xml(self):
        """
        Test fetch_tech_eu_data with malformed sitemap XML.
        """
        self.mock_client_instance_for_get_calls.get.return_value = self._mock_response(content=b"<invalid>xml</invalid>")
        
        with unittest.mock.patch('ingestion_module.funding.tech_eu.fetch.logger.exception') as mock_logger_exception: # <-- Changed here
            result = await fetch_tech_eu_data()
            
            self.assertEqual(result, {"urls": [], "paragraphs": []})
            self.mock_client_instance_for_get_calls.get.assert_called_once_with(URL)
            mock_logger_exception.assert_called_once() # Verify error logging

    # ====================================================================
    # Test extract_paragraphs function
    # ====================================================================

    async def test_extract_paragraphs_success(self):
        """
        Test that extract_paragraphs correctly extracts content from HTML.
        """
        article_html = b"""
        <html><body>
            <div class="single-post-content">
                <p>Paragraph 1 with content.</p>
                <div><span>Not a direct paragraph.</span></div>
                <p>Another paragraph.</p>
                <p>  Whitespace paragraph.  </p>
                <p></p> <!-- Empty paragraph, should be ignored -->
            </div>
            <p>Outside content div paragraph.</p>
        </body></html>
        """
        self.mock_client_instance_for_get_calls.get.return_value = self._mock_response(content=article_html)
        
        test_url = "http://test.com/article.html"
        url, paragraphs = await extract_paragraphs(self.mock_client_instance_for_get_calls, test_url)
        
        self.assertEqual(url, test_url)
        self.assertEqual(paragraphs, ["Paragraph 1 with content.", "Another paragraph.", "Whitespace paragraph."])
        self.mock_client_instance_for_get_calls.get.assert_called_once_with(test_url)

    async def test_extract_paragraphs_no_matching_div(self):
        """
        Test extract_paragraphs when the target content div is not found.
        """
        article_html = b"""
        <html><body>
            <div class="other-div">
                <p>Some content.</p>
            </div>
        </body></html>
        """
        self.mock_client_instance_for_get_calls.get.return_value = self._mock_response(content=article_html)
        
        test_url = "http://test.com/article.html"
        url, paragraphs = await extract_paragraphs(self.mock_client_instance_for_get_calls, test_url)
        
        self.assertEqual(url, test_url)
        self.assertEqual(paragraphs, []) # Should return empty list if div not found
        self.mock_client_instance_for_get_calls.get.assert_called_once_with(test_url)

    async def test_extract_paragraphs_http_error(self):
        """
        Test extract_paragraphs when fetching the article results in an HTTP error.
        """
        self.mock_client_instance_for_get_calls.get.return_value = self._mock_response(status_code=404)
        
        with unittest.mock.patch('ingestion_module.funding.tech_eu.fetch.logger.exception') as mock_logger_exception: # <-- Changed here
            test_url = "http://test.com/article.html"
            url, paragraphs = await extract_paragraphs(self.mock_client_instance_for_get_calls, test_url)
            
            self.assertEqual(url, test_url)
            self.assertEqual(paragraphs, [])
            mock_logger_exception.assert_called_once() # Verify error logging

    # ====================================================================
    # Test main function (end-to-end scenarios)
    # ====================================================================

    async def test_main_full_workflow_success(self):
        """
        Test the main function's full pipeline with successful data fetching and AI extraction.
        """
        sitemap_content = b"""
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
            <url>
                <loc>https://tech.eu/2024/01/ai-company-raises-series-b/</loc>
                <news:news><news:publication_date>2024-01-05T00:00:00Z</news:publication_date></news:news>
            </url>
        </urlset>
        """
        article_html_content = b"""
        <html><body><div class="single-post-content"><p>AI company secured $20M.</p></div></body></html>
        """
        
        # Configure side_effect for mock_client_instance_for_get_calls.get
        self.mock_client_instance_for_get_calls.get.side_effect = [
            self._mock_response(content=sitemap_content), # For sitemap
            self._mock_response(content=article_html_content) # For article content
        ]

        # Mock extracted data from AI
        mock_extracted_data = {
            "article_title": ["AI Company Raises Series B"],
            "article_link": ["https://tech.eu/2024/01/ai-company-raises-series-b/"],
            "company_name": ["AI Co"],
            "amount_raised": ["20000000"],
            "currency": ["USD"],
            "funding_round": ["Series B"]
        }
        mock_finalize_ai_extraction.return_value = mock_extracted_data
        
        # Patch fetch_tech_eu_data to return the expected links and paragraphs
        with unittest.mock.patch('ingestion_module.funding.tech_eu.fetch.fetch_tech_eu_data') as mock_fetch_tech_eu_data:
            mock_fetch_tech_eu_data.return_value = {
                "urls": ["https://tech.eu/2024/01/ai-company-raises-series-b/"],
                "paragraphs": ["AI company secured $20M."]
            }
            await tech_eu_main()
        
        # Assert that the file was opened and written to
        self.mock_aiofiles_open.assert_called_once_with("tech_eu_data.txt", "a")
        written_content = self.mock_aiofiles_open().write.call_args[0][0] # Note: write instead of writelines
        written_data = json.loads(written_content)
        
        self.assertEqual(written_data["source"], "Tech.EU")
        self.assertCountEqual(written_data["article_title"], mock_extracted_data["article_title"])
        self.assertCountEqual(written_data["company_name"], mock_extracted_data["company_name"])
        self.assertCountEqual(written_data["amount_raised"], mock_extracted_data["amount_raised"])
        
        # Verify LLM was called with the correct input
        mock_finalize_ai_extraction.assert_called_once_with(links_and_paragraphs={
            "urls": ["https://tech.eu/2024/01/ai-company-raises-series-b/"],
            "paragraphs": ["AI company secured $20M."]
        })
        
        # Verify that fetch_tech_eu_data was called once
        mock_fetch_tech_eu_data.assert_called_once()
        # No direct assertion on mock_client_instance_for_get_calls.get.call_count here
        # because fetch_tech_eu_data itself is mocked.

    async def test_main_no_data_from_fetch(self):
        """
        Test main function when fetch_tech_eu_data returns no relevant data.
        """
        # Mock fetch_tech_eu_data to return an empty dictionary
        with unittest.mock.patch('ingestion_module.funding.tech_eu.fetch.fetch_tech_eu_data', return_value={"urls": [], "paragraphs": []}):
            await tech_eu_main()
            
            # Verify no LLM call and no file write
            mock_finalize_ai_extraction.assert_not_called()
            self.mock_aiofiles_open.assert_not_called()

    async def test_main_ai_extraction_failure(self):
        """
        Test main function when AI extraction fails.
        """
        sitemap_content = b"""
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
            <url>
                <loc>https://tech.eu/2024/01/ai-company-raises-series-b/</loc>
                <news:news><news:publication_date>2024-01-05T00:00:00Z</news:publication_date></news:news>
            </url>
        </urlset>
        """
        article_html_content = b"""
        <html><body><div class="single-post-content"><p>AI company secured $20M.</p></div></body></html>
        """
        
        # Patch fetch_tech_eu_data to return the expected links and paragraphs
        with unittest.mock.patch('ingestion_module.funding.tech_eu.fetch.fetch_tech_eu_data') as mock_fetch_tech_eu_data:
            mock_fetch_tech_eu_data.return_value = {
                "urls": ["https://tech.eu/2024/01/ai-company-raises-series-b/"],
                "paragraphs": ["AI company secured $20M."]
            }
            # Mock LLM extraction to raise an exception
            mock_finalize_ai_extraction.side_effect = Exception("AI extraction failed")
            
            with unittest.mock.patch('ingestion_module.funding.tech_eu.fetch.logger') as mock_logger:
                await tech_eu_main()
                
                # Verify LLM was called, but no file written due to failure
                mock_finalize_ai_extraction.assert_called_once()
                self.mock_aiofiles_open.assert_not_called()
                mock_logger.error.assert_called_once_with("Failed to extract AI content from Tech_EU's data: AI extraction failed")

    async def test_main_no_extracted_data_from_ai(self):
        """
        Test main function when AI extraction returns an empty dictionary.
        """
        sitemap_content = b"""
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
            <url>
                <loc>https://tech.eu/2024/01/ai-company-raises-series-b/</loc>
                <news:news><news:publication_date>2024-01-05T00:00:00Z</news:publication_date></news:news>
            </url>
        </urlset>
        """
        article_html_content = b"""
        <html><body><div class="single-post-content"><p>AI company secured $20M.</p></div></body></html>
        """
        
        # Patch fetch_tech_eu_data to return the expected links and paragraphs
        with unittest.mock.patch('ingestion_module.funding.tech_eu.fetch.fetch_tech_eu_data') as mock_fetch_tech_eu_data:
            mock_fetch_tech_eu_data.return_value = {
                "urls": ["https://tech.eu/2024/01/ai-company-raises-series-b/"],
                "paragraphs": ["AI company secured $20M."]
            }
            # Mock LLM extraction to return an empty dictionary
            mock_finalize_ai_extraction.return_value = {}
            
            with unittest.mock.patch('ingestion_module.funding.tech_eu.fetch.logger') as mock_logger:
                await tech_eu_main()
                
                # Verify LLM was called, but no file written
                mock_finalize_ai_extraction.assert_called_once()
                self.mock_aiofiles_open.assert_not_called()
                mock_logger.warning.assert_called_once_with("AI extraction for Tech_eu returned no data. No logging will happen")