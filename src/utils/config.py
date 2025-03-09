"""
Configuration module for the web scraper project.
Loads settings from environment variables.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
LOGS_DIR = ROOT_DIR / "logs"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

class Config:
    """
    Configuration class for the web scraper application.
    """
    # Scraping settings
    USER_AGENT = os.getenv(
        'USER_AGENT', 
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    )
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))
    REQUEST_DELAY = float(os.getenv('REQUEST_DELAY', 1.0))  # Delay between requests in seconds
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
    
    # Proxy settings (optional)
    USE_PROXY = os.getenv('USE_PROXY', 'False').lower() in ('true', '1', 't')
    PROXY_URL = os.getenv('PROXY_URL', '')
    
    # Database settings (for storing scraped data)
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'scraper_db')
    DB_USER = os.getenv('DB_USER', '')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', str(LOGS_DIR / 'scraper.log'))
    
    # File paths
    RAW_DATA_PATH = str(RAW_DATA_DIR)
    PROCESSED_DATA_PATH = str(PROCESSED_DATA_DIR)
    
    @classmethod
    def setup_logging(cls):
        """
        Setup logging configuration.
        """
        numeric_level = getattr(logging, cls.LOG_LEVEL.upper(), None)
        if not isinstance(numeric_level, int):
            numeric_level = logging.INFO
            
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(cls.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        
        # Reduce noise from third-party libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        
        return logging.getLogger('web_scraper') 