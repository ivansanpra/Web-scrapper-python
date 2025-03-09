"""
Tests for the BaseScraper class.
"""
import unittest
from unittest.mock import patch, MagicMock
import requests
from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper


class TestBaseScraper(unittest.TestCase):
    """
    Test cases for the BaseScraper class.
    """
    
    def setUp(self):
        """
        Set up the test environment.
        """
        self.base_url = "https://example.com"
        self.scraper = BaseScraper(self.base_url)
    
    def test_initialization(self):
        """
        Test that the scraper initializes correctly.
        """
        self.assertEqual(self.scraper.base_url, self.base_url)
        self.assertIsNotNone(self.scraper.headers)
        self.assertIsNotNone(self.scraper.session)
        self.assertIsNotNone(self.scraper.logger)
    
    def test_custom_headers(self):
        """
        Test that custom headers are properly set.
        """
        custom_headers = {"User-Agent": "CustomBot/1.0", "Accept": "text/html"}
        scraper = BaseScraper(self.base_url, headers=custom_headers)
        
        self.assertEqual(scraper.headers, custom_headers)
        self.assertEqual(scraper.session.headers["User-Agent"], "CustomBot/1.0")
        self.assertEqual(scraper.session.headers["Accept"], "text/html")
    
    @patch('requests.Session.get')
    def test_get_page_success(self, mock_get):
        """
        Test the get_page method when successful.
        """
        # Setup mock
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Call method
        response = self.scraper.get_page(f"{self.base_url}/test")
        
        # Assertions
        mock_get.assert_called_once_with(f"{self.base_url}/test", params=None)
        self.assertEqual(response, mock_response)
    
    @patch('requests.Session.get')
    def test_get_page_error(self, mock_get):
        """
        Test the get_page method when an error occurs.
        """
        # Setup mock
        mock_get.side_effect = requests.exceptions.RequestException("Error")
        
        # Call method and check for exception
        with self.assertRaises(requests.exceptions.RequestException):
            self.scraper.get_page(f"{self.base_url}/test")
    
    def test_parse_html(self):
        """
        Test the parse_html method.
        """
        # Setup
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Test</h1></body></html>"
        
        # Call method
        soup = self.scraper.parse_html(mock_response)
        
        # Assertions
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(soup.h1.text, "Test")
    
    def test_scrape_not_implemented(self):
        """
        Test that the scrape method raises NotImplementedError.
        """
        with self.assertRaises(NotImplementedError):
            self.scraper.scrape()
    
    def test_clean_data(self):
        """
        Test the clean_data method.
        """
        test_data = {"test": "data"}
        self.assertEqual(self.scraper.clean_data(test_data), test_data)


if __name__ == '__main__':
    unittest.main() 