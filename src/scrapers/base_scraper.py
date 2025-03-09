"""
Base scraper class for web scraping.
"""
import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, Any, Optional

class BaseScraper:
    """
    Base class for all scrapers.
    Provides common functionality and interface for scraping operations.
    """
    
    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None):
        """
        Initialize the scraper with a base URL and optional headers.
        
        Args:
            base_url: The base URL for the scraper
            headers: Optional HTTP headers to use for requests
        """
        self.base_url = base_url
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def setup(self):
        """
        Perform any setup required before scraping.
        For example, login, collecting session cookies, etc.
        """
        pass
        
    def get_page(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Get a page from the website.
        
        Args:
            url: The URL to request
            params: Optional query parameters
            
        Returns:
            Response object from the request
        """
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching {url}: {e}")
            raise
    
    def parse_html(self, response: requests.Response) -> BeautifulSoup:
        """
        Parse HTML from a response.
        
        Args:
            response: Response object from requests
            
        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(response.text, 'html.parser')
    
    def scrape(self):
        """
        Main scraping method. Should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement scrape()")
        
    def clean_data(self, data: Any) -> Any:
        """
        Clean and format the scraped data.
        
        Args:
            data: The raw scraped data
            
        Returns:
            Cleaned data
        """
        return data
    
    def save_data(self, data: Any, filename: str):
        """
        Save the scraped data to a file.
        
        Args:
            data: The data to save
            filename: The name of the file to save to
        """
        pass 