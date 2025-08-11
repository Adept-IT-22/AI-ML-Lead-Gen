import unittest
import unittest.mock
import httpx
import asyncio
import json
import logging
import aiofiles
import copy
from typing import List, Dict, Union, Any

# Adjust path to allow imports from parent directories (e.g., utils.data_structures)
# This ensures that the test script can find modules relative to the project root.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import the functions and variables from the original hacker_news fetch file.
# Note the corrected module path: 'hacker_news' instead of 'hackernews'.
from ingestion_module.ai_extraction.extract_hiring_content import finalize_ai_extraction
from ingestion_module.hiring.hacker_news.fetch import (
    URL,
    fetch_hackernews_jobs,
    get_all_job_details,
    get_individual_job_details,
    dict_of_lists,
    main as hackernews_main, # Renaming 'main' to avoid conflict in test file
    hiring_fetched_data # Access the original data structure
)

# Mock external dependencies
# Mock the LLM function 'finalize_ai_extraction'
mock_finalize_ai_extraction = unittest.mock.AsyncMock()

# Define a mock for the 'hiring_fetched_data' dictionary structure.
# This ensures tests use a predictable initial state for data.
mock_hiring_fetched_data = {
    "type": "hiring",
    "job_id": [],
    "job_title": [],
    "job_url": [],
    "job_text": [],
    "job_time": [],
    "company_name": [],
    "company_city": [],
    "company_country": [],
    "company_decision_makers": [],
    "job_tags": [],
    "source": ""
}

# Suppress logging output during tests for cleaner console output.
# You can adjust this level if you need to see specific logs during debugging.
logging.disable(logging.CRITICAL)


class TestHackerNewsFetcher(unittest.IsolatedAsyncioTestCase):
    """
    Unit tests for the HackerNews job fetching and processing module.
    Each test method runs in its own isolated asyncio event loop.
    """

    async def asyncSetUp(self):
        """
        Set up mocks and patches before each individual test method runs.
        This ensures a clean and isolated test environment for every test.
        """
        # Reset the mock's call history and return values for a fresh start.
        mock_finalize_ai_extraction.reset_mock()
        
        # Create a mock instance of httpx.AsyncClient.
        # This will be the 'client' object used within the 'async with' block in main.
        self.mock_client_instance = unittest.mock.AsyncMock(spec=httpx.AsyncClient)
        
        # Create a mock for 'aiofiles.open' to prevent actual file I/O during tests.
        self.mock_aiofiles_open = unittest.mock.mock_open()
        
        # Create a mock for the httpx.AsyncClient class itself.
        # This mock needs to behave as an asynchronous context manager.
        # When 'httpx.AsyncClient()' is called in the main function, this mock will be returned.
        mock_httpx_client_class = unittest.mock.AsyncMock()
        
        # Configure the mock's '__aenter__' method.
        # This method is called when 'async with' is entered. It must be a coroutine
        # and return the 'self.mock_client_instance' that we want to control.
        mock_httpx_client_class.__aenter__.return_value = self.mock_client_instance

        # Configure the mock's '__aexit__' method.
        # This method is called when 'async with' is exited. It must also be a coroutine.
        mock_httpx_client_class.__aexit__.return_value = None 

        # Set up patches to replace real objects with mocks in the module under test.
        # The target string specifies the exact path to the object being patched.
        self.patcher_finalize_ai_extraction = unittest.mock.patch(
            'ingestion_module.hiring.hacker_news.fetch.finalize_ai_extraction', 
            new=mock_finalize_ai_extraction
        )
        self.patcher_aiofiles_open = unittest.mock.patch(
            'ingestion_module.hiring.hacker_news.fetch.aiofiles.open', 
            new=self.mock_aiofiles_open
        )
        self.patcher_hiring_data_dict = unittest.mock.patch(
            'ingestion_module.hiring.hacker_news.fetch.hiring_fetched_data',
            new=mock_hiring_fetched_data
        )
        # Patch httpx.AsyncClient at the module level.
        # This ensures that when 'httpx.AsyncClient()' is called in the 'fetch' module,
        # it returns our 'mock_httpx_client_class' which then provides 'self.mock_client_instance'.
        self.patcher_httpx_client_class = unittest.mock.patch(
            'ingestion_module.hiring.hacker_news.fetch.httpx.AsyncClient',
            new=mock_httpx_client_class
        )

        # Start all the defined patchers.
        self.patcher_finalize_ai_extraction.start()
        self.patcher_aiofiles_open.start()
        self.patcher_hiring_data_dict.start()
        self.patcher_httpx_client_class.start()

    async def asyncTearDown(self):
        """
        Clean up after each test method by stopping all active patchers.
        This restores the original state of the patched objects.
        """
        self.patcher_finalize_ai_extraction.stop()
        self.patcher_aiofiles_open.stop()
        self.patcher_hiring_data_dict.stop()
        self.patcher_httpx_client_class.stop()
        # Re-enable logging after tests are complete.
        logging.disable(logging.NOTSET)

    def _mock_response(self, status_code=200, json_data=None, content=b'', headers=None):
        """
        Helper method to create a mock httpx.Response object.
        Configures status code, JSON data, content, and headers for the mock response.
        """
        mock_response = unittest.mock.Mock(spec=httpx.Response)
        mock_response.status_code = status_code
        if json_data is not None:
            # If JSON data is provided, set the mock's .json() method return value
            # and encode the JSON data as content.
            mock_response.json.return_value = json_data
            mock_response.content = json.dumps(json_data).encode('utf-8')
            mock_response.text = json.dumps(json_data)
        else:
            # Otherwise, use raw content.
            mock_response.content = content
            mock_response.text = content.decode('utf-8')
        mock_response.headers = headers if headers is not None else {}
        # By default, assume raise_for_status() does nothing (success).
        mock_response.raise_for_status.return_value = None
        # If status code indicates an error (>= 400), configure raise_for_status()
        # to raise an httpx.HTTPStatusError.
        if status_code >= 400:
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                f"Bad status code: {status_code}", request=httpx.Request("GET", "[http://test.com](http://test.com)"), response=mock_response
            )
        return mock_response

    # --- Test fetch_hackernews_jobs function ---

    async def test_fetch_hackernews_jobs_success(self):
        """
        Test that fetch_hackernews_jobs successfully fetches job IDs.
        """
        job_ids = [123, 456, 789]
        # Configure the mock client's .get() method to return a mock response with job IDs.
        self.mock_client_instance.get.return_value = self._mock_response(json_data=job_ids)
        
        result = await fetch_hackernews_jobs(self.mock_client_instance, URL)
        
        self.assertEqual(result, job_ids)
        # Assert that the mock client's .get() method was called exactly once with the correct URL.
        self.mock_client_instance.get.assert_called_once_with(f"{URL}jobstories.json")

    async def test_fetch_hackernews_jobs_http_error(self):
        """
        Test that fetch_hackernews_jobs handles HTTP errors gracefully.
        """
        # Configure the mock client's .get() method to return an error status code.
        self.mock_client_instance.get.return_value = self._mock_response(status_code=500)
        
        result = await fetch_hackernews_jobs(self.mock_client_instance, URL)
        
        # The function should return None on exception, as per its implementation.
        self.assertIsNone(result)

    # --- Test get_individual_job_details function ---

    async def test_get_individual_job_details_success(self):
        """
        Test that get_individual_job_details fetches a single job's details.
        """
        job_id = 123
        job_data = {"id": 123, "title": "Software Engineer", "url": "[http://example.com/job1](http://example.com/job1)"}
        self.mock_client_instance.get.return_value = self._mock_response(json_data=job_data)
        
        result = await get_individual_job_details(self.mock_client_instance, job_id, URL)
        
        self.assertEqual(result, job_data)
        self.mock_client_instance.get.assert_called_once_with(f"{URL}item/{job_id}.json?print=pretty")

    async def test_get_individual_job_details_http_error(self):
        """
        Test that get_individual_job_details handles HTTP errors.
        """
        job_id = 123
        self.mock_client_instance.get.return_value = self._mock_response(status_code=404)
        
        result = await get_individual_job_details(self.mock_client_instance, job_id, URL)
        
        self.assertIsNone(result)

    # --- Test get_all_job_details function ---

    async def test_get_all_job_details_success(self):
        """
        Test that get_all_job_details fetches details for multiple job IDs.
        """
        job_ids = [1, 2]
        job_details_1 = {"id": 1, "title": "AI Engineer"}
        job_details_2 = {"id": 2, "title": "ML Scientist"}

        # Patch 'get_individual_job_details' to control its behavior directly.
        # This avoids making actual HTTP requests for individual jobs in this test.
        with unittest.mock.patch('ingestion_module.hiring.hacker_news.fetch.get_individual_job_details') as mock_get_individual:
            mock_get_individual.side_effect = [
                job_details_1,
                job_details_2
            ]
            
            result = await get_all_job_details(self.mock_client_instance, job_ids, URL)
            
            # Use assertCountEqual as the order of results from asyncio.as_completed is not guaranteed.
            self.assertCountEqual(result, [job_details_1, job_details_2])
            self.assertEqual(mock_get_individual.call_count, 2)
            mock_get_individual.assert_any_call(self.mock_client_instance, 1, URL)
            mock_get_individual.assert_any_call(self.mock_client_instance, 2, URL)

    async def test_get_all_job_details_some_failures(self):
        """
        Test that get_all_job_details handles partial failures of individual job fetches.
        """
        job_ids = [1, 2, 3]
        job_details_1 = {"id": 1, "title": "AI Engineer"}
        job_details_3 = {"id": 3, "title": "Deep Learning Researcher"}

        with unittest.mock.patch('ingestion_module.hiring.hacker_news.fetch.get_individual_job_details') as mock_get_individual:
            mock_get_individual.side_effect = [
                job_details_1,
                None, # Simulate a failure (e.g., HTTP error) for job ID 2
                job_details_3
            ]
            
            result = await get_all_job_details(self.mock_client_instance, job_ids, URL)
            
            # The function should still return successfully fetched jobs, and None for failed ones.
            self.assertCountEqual(result, [job_details_1, job_details_3, None]) 
            self.assertEqual(mock_get_individual.call_count, 3)

    # --- Test dict_of_lists function ---

    def test_dict_of_lists_filters_ai_jobs(self):
        """
        Test that dict_of_lists correctly filters jobs based on AI keywords
        and transforms the list of dictionaries into a dictionary of lists.
        """
        all_jobs = [
            {"id": 1, "title": "Software Engineer (AI)", "url": "[http://example.com/ai-job](http://example.com/ai-job)", "by": "user1", "score": 10, "text": "AI related text", "time": 123},
            {"id": 2, "title": "Frontend Developer", "url": "[http://example.com/frontend](http://example.com/frontend)", "by": "user2", "score": 5, "text": "Frontend text", "time": 456},
            {"id": 3, "title": "Machine Learning Engineer", "url": "[http://example.com/ml-job](http://example.com/ml-job)", "by": "user3", "score": 15, "text": "ML related text", "time": 789},
            {"id": 4, "title": "Data Scientist (NLP)", "url": "[http://example.com/nlp-job](http://example.com/nlp-job)", "by": "user4", "score": 20, "text": "NLP related text", "time": 101},
            {"id": 5, "title": "General Manager", "url": "[http://example.com/general](http://example.com/general)", "by": "user5", "score": 2, "text": "General text", "time": 112},
            {"id": 6, "title": "Deep Learning Researcher", "url": "[http://example.com/dl-job](http://example.com/dl-job)", "by": "user6", "score": 25, "text": "DL related text", "time": 131},
            {"id": 7, "title": "Computer Vision Engineer", "url": "[http://example.com/cv-job](http://example.com/cv-job)", "by": "user7", "score": 30, "text": "CV related text", "time": 141},
            {"id": 8, "title": "AI Product Manager", "url": "[http://example.com/ai-pm](http://example.com/ai-pm)", "by": "user8", "score": 12, "text": "AI product text", "time": 151},
        ]
        
        result = dict_of_lists(all_jobs)
        
        self.assertEqual(result["type"], "job")
        self.assertCountEqual(result["id"], [1, 3, 4, 6, 7, 8])
        self.assertCountEqual(result["title"], [
            "Software Engineer (AI)", "Machine Learning Engineer", "Data Scientist (NLP)",
            "Deep Learning Researcher", "Computer Vision Engineer", "AI Product Manager"
        ])
        self.assertCountEqual(result["url"], [
            "[http://example.com/ai-job](http://example.com/ai-job)", "[http://example.com/ml-job](http://example.com/ml-job)", "[http://example.com/nlp-job](http://example.com/nlp-job)",
            "[http://example.com/dl-job](http://example.com/dl-job)", "[http://example.com/cv-job](http://example.com/cv-job)", "[http://example.com/ai-pm](http://example.com/ai-pm)"
        ])
        self.assertCountEqual(result["by"], ["user1", "user3", "user4", "user6", "user7", "user8"])
        self.assertCountEqual(result["score"], [10, 15, 20, 25, 30, 12])
        self.assertCountEqual(result["text"], [
            "AI related text", "ML related text", "NLP related text",
            "DL related text", "CV related text", "AI product text"
        ])
        self.assertCountEqual(result["time"], [123, 789, 101, 131, 141, 151])

    def test_dict_of_lists_empty_input(self):
        """
        Test dict_of_lists with an empty list input.
        """
        result = dict_of_lists([])
        self.assertEqual(result, {
            "type": "job", "by": [], "id": [], "score": [], "text": [], "time": [], "title": [], "url": []
        })

    def test_dict_of_lists_missing_keys_in_job(self):
        """
        Test dict_of_lists when some job dictionaries are missing expected keys.
        """
        all_jobs = [
            {"id": 1, "title": "AI Job", "url": "[http://example.com/ai](http://example.com/ai)", "by": "user1"}, # Missing score, text, time
            {"id": 2, "title": "ML Role", "url": "[http://example.com/ml](http://example.com/ml)", "score": 10}, # Missing by, text, time
        ]
        result = dict_of_lists(all_jobs)
        
        self.assertCountEqual(result["id"], [1, 2])
        self.assertCountEqual(result["by"], ["user1", ""]) # Should append empty string for missing 'by'
        self.assertCountEqual(result["score"], ["", 10])
        self.assertCountEqual(result["text"], ["", ""])
        self.assertCountEqual(result["time"], ["", ""])

    # --- Test main function (end-to-end scenarios) ---

    async def test_main_success_with_ai_jobs(self):
        """
        Test the main function's full pipeline when AI-related jobs are found and processed.
        """
        # Configure mock responses for HTTP requests in the order they are expected.
        self.mock_client_instance.get.side_effect = [
            # 1. Response for fetch_hackernews_jobs (returns a list of job IDs)
            self._mock_response(json_data=[101, 102, 103]),
            # 2. Response for get_individual_job_details (ID 101 - AI job)
            self._mock_response(json_data={"id": 101, "title": "AI Engineer Position", "url": "[http://example.com/ai-job](http://example.com/ai-job)", "by": "compA", "score": 50, "text": "AI job description", "time": 1678886400}),
            # 3. Response for get_individual_job_details (ID 102 - non-AI job, will be filtered out)
            self._mock_response(json_data={"id": 102, "title": "Frontend Dev", "url": "[http://example.com/frontend-job](http://example.com/frontend-job)", "by": "compB", "score": 30, "text": "Frontend job description", "time": 1678886500}),
            # 4. Response for get_individual_job_details (ID 103 - ML job)
            self._mock_response(json_data={"id": 103, "title": "Machine Learning Scientist", "url": "[http://example.com/ml-job](http://example.com/ml-job)", "by": "compC", "score": 60, "text": "ML job description", "time": 1678886600}),
        ]

        # Configure the mock LLM extraction function to return expected processed data.
        mock_finalize_ai_extraction.return_value = {
            "job_id": [101, 103],
            "job_title": ["AI Engineer Position", "Machine Learning Scientist"],
            "job_url": ["[http://example.com/ai-job](http://example.com/ai-job)", "[http://example.com/ml-job](http://example.com/ml-job)"],
            "company_name": ["Company A", "Company C"],
            "job_tags": [["AI"], ["ML"]]
        }
        
        # Run the main function of the HackerNews fetcher.
        await hackernews_main()
        
        # Assert that the file was attempted to be opened for writing.
        self.mock_aiofiles_open.assert_called_once_with("hackernews_data.txt", "a")
        
        # Retrieve the content that would have been written to the file and parse it.
        written_content = self.mock_aiofiles_open().writelines.call_args[0][0]
        written_data = json.loads(written_content)
        
        # Assertions on the final processed data structure.
        self.assertEqual(written_data["type"], "hiring")
        self.assertCountEqual(written_data["job_id"], [101, 103])
        self.assertCountEqual(written_data["job_title"], ["AI Engineer Position", "Machine Learning Scientist"])
        self.assertCountEqual(written_data["job_url"], ["[http://example.com/ai-job](http://example.com/ai-job)", "[http://example.com/ml-job](http://example.com/ml-job)"])
        self.assertCountEqual(written_data["company_name"], ["Company A", "Company C"])
        self.assertCountEqual(written_data["job_tags"], [["AI"], ["ML"]])
        # Verify 'company_decision_makers' is populated from the 'by' field of filtered jobs.
        self.assertCountEqual(written_data["company_decision_makers"], ["compA", "compC"]) 
        self.assertEqual(written_data["source"], "HackerNews")
        
        # Verify that the LLM extraction function was called once with the correct filtered input.
        mock_finalize_ai_extraction.assert_called_once_with({
            "ids": [101, 103],
            "urls": ["[http://example.com/ai-job](http://example.com/ai-job)", "[http://example.com/ml-job](http://example.com/ml-job)"],
            "titles": ["AI Engineer Position", "Machine Learning Scientist"]
        })
        
        # Verify the total number of HTTP GET requests made by the mock client.
        # (1 for jobstories.json + 3 for individual job details).
        self.assertEqual(self.mock_client_instance.get.call_count, 4)

    async def test_main_no_jobs_fetched(self):
        """
        Test the main function when no job IDs are initially fetched.
        """
        # Mock 'fetch_hackernews_jobs' to return an empty list of IDs.
        self.mock_client_instance.get.return_value = self._mock_response(json_data=[])
        
        await hackernews_main()
        
        # Assert that the LLM was not called and no file was written, as there's no data.
        mock_finalize_ai_extraction.assert_not_called()
        self.mock_aiofiles_open.assert_not_called()
        # Only the initial 'jobstories.json' request should have occurred.
        self.assertEqual(self.mock_client_instance.get.call_count, 1)

    async def test_main_no_ai_jobs_after_filtering(self):
        """
        Test the main function when jobs are fetched but none are AI-related after filtering.
        """
        # Mock responses for fetching job IDs and individual job details (non-AI related).
        self.mock_client_instance.get.side_effect = [
            self._mock_response(json_data=[101, 102]), # Job IDs
            self._mock_response(json_data={"id": 101, "title": "Regular Dev", "url": "[http://example.com/dev](http://example.com/dev)", "by": "user1", "score": 10, "text": "desc", "time": 1}),
            self._mock_response(json_data={"id": 102, "title": "Project Manager", "url": "[http://example.com/pm](http://example.com/pm)", "by": "user2", "score": 20, "text": "desc", "time": 2}),
        ]
        
        await hackernews_main()
        
        # The LLM should still be called, but with empty input data, as per the original code's flow.
        # The 'if extracted_data:' check in main will then prevent file writing.
        mock_finalize_ai_extraction.assert_called_once_with({
            "ids": [],
            "urls": [],
            "titles": []
        })
        self.mock_aiofiles_open.assert_not_called()
        # All HTTP requests (1 for jobstories, 2 for individual jobs) should have occurred.
        self.assertEqual(self.mock_client_instance.get.call_count, 3)

    async def test_main_llm_extraction_failure(self):
        """
        Test the main function's behavior when the LLM extraction fails.
        """
        # Mock responses for fetching job IDs and an AI-related job.
        self.mock_client_instance.get.side_effect = [
            self._mock_response(json_data=[101]),
            self._mock_response(json_data={"id": 101, "title": "AI Job", "url": "[http://example.com/ai](http://example.com/ai)", "by": "user1", "score": 10, "text": "desc", "time": 1}),
        ]

        # Configure the LLM mock to raise an exception, simulating a failure.
        mock_finalize_ai_extraction.side_effect = Exception("LLM API error")
        
        await hackernews_main()
        
        # The LLM should still be called once, but no file should be written due to the extraction failure.
        mock_finalize_ai_extraction.assert_called_once()
        self.mock_aiofiles_open.assert_not_called()
        # All HTTP requests should still have occurred.
        self.assertEqual(self.mock_client_instance.get.call_count, 2)