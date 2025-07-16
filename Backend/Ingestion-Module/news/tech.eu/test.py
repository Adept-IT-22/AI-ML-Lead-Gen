import unittest
from unittest.mock import patch, MagicMock
from fetch import fetch_tech_eu_data

sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:n="http://www.google.com/schemas/sitemap-news/0.9">
    <url>
        <loc>https://tech.eu/article</loc>
        <n:news>
            <n:publication>
                <n:name>Tech.eu</n:name>
                <n:language>en</n:language>
            </n:publication>
            <n:publication_date>2025-07-16T00:00:00+00:00</n:publication_date>
            <n:title>$5M Funding for AI Startup</n:title>
            <n:keywords><![CDATA[OpenAI, Sam Altman]]></n:keywords>
        </n:news>
    </url>
</urlset>
"""

class TestFetchTechEu(unittest.TestCase):

    @patch("fetch.requests.get")
    def test_response_data_parses_correctly(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sample_xml.encode("utf-8")
        mock_get.return_value = mock_response

        data = fetch_tech_eu_data()
        
        self.assertEqual(data["article_link"][0], "https://tech.eu/article")
        self.assertEqual(data["amount_raised"][0], 5_000_000)
        self.assertEqual(data["currency"][0], "$")
        self.assertEqual(data["company_name"][0], "OpenAI")
        self.assertEqual(data["article_date"][0], "2025-07-16")
        self.assertEqual(data["article_time"][0], "00:00:00+00:00")
        self.assertEqual(data["keywords"][0][0], "OpenAI, Sam Altman")
        

        #Make sure all the arrays in the dictionary are the same length
        lengths = [len(data[key]) for key in data]
        assert len(set(lengths)) == 1 

if __name__ == "__main__":
    unittest.main()
