"""
Main entry point for the web scraper.
"""
import argparse
import logging
import sys
from pathlib import Path

# Add the parent directory to the sys.path to allow importing from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import Config
from src.scrapers.base_scraper import BaseScraper
# Import specific scrapers here when implemented
# from src.scrapers.example_scraper import ExampleScraper


def parse_args():
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Web scraper')
    parser.add_argument(
        '--target',
        type=str,
        choices=['all', 'example'],  # Update with your scraper targets
        default='all',
        help='Scraper target to run'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='json',
        choices=['json', 'csv', 'excel'],
        help='Output format'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    return parser.parse_args()


def main():
    """
    Main function to run the scraper.
    """
    args = parse_args()
    
    # Setup logging
    if args.debug:
        Config.LOG_LEVEL = 'DEBUG'
    logger = Config.setup_logging()
    
    logger.info("Starting web scraper")
    logger.debug(f"Arguments: {args}")
    
    # Initialize and run the appropriate scraper
    if args.target == 'all':
        logger.info("Running all scrapers")
        # Implement code to run all scrapers
        pass
    elif args.target == 'example':
        logger.info("Running example scraper")
        # Example implementation:
        # scraper = ExampleScraper(base_url="https://example.com")
        # scraper.setup()
        # data = scraper.scrape()
        # output_path = Path(Config.PROCESSED_DATA_PATH) / f"example_data.{args.output}"
        # if args.output == 'json':
        #     from src.utils.helpers import save_to_json
        #     save_to_json(data, output_path)
        # elif args.output == 'csv':
        #     from src.utils.helpers import save_to_csv
        #     save_to_csv(data, output_path)
        # elif args.output == 'excel':
        #     from src.utils.helpers import save_to_excel
        #     save_to_excel(data, output_path)
        pass
    else:
        logger.error(f"Unknown target: {args.target}")
        return 1
    
    logger.info("Web scraper completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 