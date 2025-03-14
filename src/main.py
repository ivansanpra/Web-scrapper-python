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
from src.scrapers.chedraui_scraper import ChedrauiScraper
from src.scrapers.walmart_scraper import WalmartScraper


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
        choices=['all', 'example', 'chedraui', 'walmart'],  # Added 'walmart' option
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
    parser.add_argument(
        '--products',
        type=str,
        nargs='+',
        default=['aguacate', 'jitomate', 'manzana'],
        help='Product types to search for (e.g., aguacate jitomate manzana)'
    )
    parser.add_argument(
        '--method',
        type=str,
        choices=['api', 'html', 'both'],
        default='api',
        help='Method to use for scraping: api, html, or both'
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
        # Run the Chedraui scraper
        run_chedraui_scraper(args.output, args.products, args.method)
        # Run the Walmart scraper
        run_walmart_scraper(args.output, args.products, args.method)
        # Add other scrapers here when implemented
    elif args.target == 'chedraui':
        logger.info("Running Chedraui scraper")
        run_chedraui_scraper(args.output, args.products, args.method)
    elif args.target == 'walmart':
        logger.info("Running Walmart scraper")
        run_walmart_scraper(args.output, args.products, args.method)
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


def run_chedraui_scraper(output_format, product_types=None, method='api'):
    """
    Run the Chedraui scraper.
    
    Args:
        output_format: Format to save the data (json, csv, excel)
        product_types: List of product types to search for (e.g., ["aguacate", "jitomate", "manzana"])
        method: Method to use for scraping (api, html, or both)
    """
    logger = logging.getLogger('web_scraper')
    product_list = product_types or ["aguacate", "jitomate", "manzana"]
    logger.info(f"Initializing Chedraui scraper for products: {', '.join(product_list)}")
    
    try:
        # Initialize the scraper with the specified product types and method
        use_api = (method == 'api' or method == 'both')
        scraper = ChedrauiScraper(product_types=product_list, use_api=use_api)
        
        # Log the search URLs
        logger.info("Search URLs:")
        for product in product_list:
            search_url = f"{scraper.base_url}/{product}?_q={product}&map=ft" 
            logger.info(f" - {product}: {search_url}")
        
        # Run any setup
        scraper.setup()
        
        # Execute the scraping
        logger.info(f"Scraping Chedraui for prices of: {', '.join(product_list)}")
        data = scraper.scrape()
        
        # Save the results
        scraper.save_results(data, output_format)
        
        logger.info("Chedraui scraping completed successfully")
    except Exception as e:
        logger.error(f"Error running Chedraui scraper: {e}", exc_info=True)


def run_walmart_scraper(output_format, product_types=None, method='api'):
    """
    Run the Walmart Mexico scraper.
    
    Args:
        output_format: Format to save the data (json, csv, excel)
        product_types: List of product types to search for (e.g., ["platano", "manzana", "aguacate"])
        method: Method to use for scraping (api, html, or both)
    """
    logger = logging.getLogger('web_scraper')
    product_list = product_types or ["platano", "manzana", "aguacate"]
    logger.info(f"Initializing Walmart Mexico scraper for products: {', '.join(product_list)}")
    
    try:
        # Initialize the scraper with the specified product types and method
        use_api = (method == 'api' or method == 'both')
        scraper = WalmartScraper(product_types=product_list, use_api=use_api)
        
        # Log the search URLs
        logger.info("Search URLs:")
        for product in product_list:
            search_url = f"{scraper.base_url}/search?q={product}" 
            logger.info(f" - {product}: {search_url}")
        
        # Run any setup
        scraper.setup()
        
        # Execute the scraping
        logger.info(f"Scraping Walmart Mexico for prices of: {', '.join(product_list)}")
        data = scraper.scrape()
        
        # Save the results
        scraper.save_results(data, output_format)
        
        logger.info("Walmart Mexico scraping completed successfully")
    except Exception as e:
        logger.error(f"Error running Walmart Mexico scraper: {e}", exc_info=True)


if __name__ == "__main__":
    sys.exit(main()) 