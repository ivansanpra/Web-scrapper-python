"""
Script to test the Chedraui scraper with a local sample HTML file.
This allows testing and refining the scraper without making HTTP requests.
"""
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.scrapers.chedraui_scraper import ChedrauiScraper
from src.utils.config import Config

def parse_args():
    """
    Parse command line arguments for the script.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Test Chedraui scraper with sample HTML file or API')
    parser.add_argument(
        '--sample',
        type=str,
        default='data/sample.html',
        help='Path to the sample HTML file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='all',
        choices=['json', 'csv', 'excel', 'all'],
        help='Output format(s) for the data'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--method',
        type=str,
        choices=['api', 'html', 'sample'],
        default='sample',
        help='Method to use for testing: api (live API), html (live HTML scraping), or sample (local file)'
    )
    parser.add_argument(
        '--products',
        type=str,
        nargs='+',
        default=['manzana'],
        help='Product types to search for when using API or HTML methods'
    )
    return parser.parse_args()

def main():
    """
    Run the Chedraui scraper on a sample HTML file or with the API.
    """
    # Parse arguments
    args = parse_args()
    
    # Setup logging
    if args.debug:
        Config.LOG_LEVEL = 'DEBUG'
    logger = Config.setup_logging()
    
    # Check if using sample file
    if args.method == 'sample':
        sample_path = Path(args.sample)
        if not sample_path.exists():
            logger.error(f"Sample file not found: {sample_path}")
            return 1
            
        logger.info(f"Testing Chedraui scraper with sample file: {sample_path}")
    
    try:
        # Initialize the scraper with API preference based on method
        use_api = (args.method == 'api')
        scraper = ChedrauiScraper(use_api=use_api)
        
        # Get data based on selected method
        if args.method == 'sample':
            data = scraper.scrape_from_sample(str(sample_path))
        else:  # 'api' or 'html'
            data = scraper.scrape(args.products)
        
        # Save results in requested format(s)
        if args.output == 'all':
            scraper.save_results(data, "json")
            scraper.save_results(data, "csv")
            scraper.save_results(data, "excel")
        else:
            scraper.save_results(data, args.output)
        
        # Print a summary of the results
        print("\nScraping Results Summary:")
        print("--------------------------")
        
        for product_type, products in data.items():
            print(f"\n{product_type.upper()} products found: {len(products)}")
            if products:
                print("\nTop 5 results:")
                for i, product in enumerate(products[:5]):
                    source = product.get("source", "unknown")
                    print(f"  {i+1}. {product['name']}: {product['price_text']} (Source: {source})")
        
        print(f"\nData saved to {Config.PROCESSED_DATA_PATH}")
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 