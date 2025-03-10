"""
Script to run the Chedraui scraper directly.
This is useful for testing the scraper without going through the main CLI.
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
    parser = argparse.ArgumentParser(description='Run Chedraui scraper for product prices')
    parser.add_argument(
        '--products',
        type=str,
        nargs='+',
        default=['aguacate', 'jitomate', 'manzana'],
        help='List of product types to search for (e.g., aguacate jitomate manzana)'
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
        choices=['api', 'html', 'both'],
        default='api',
        help='Method to use: api (GraphQL API, faster and more reliable), html (HTML scraping), or both'
    )
    return parser.parse_args()

def main():
    """
    Run the Chedraui scraper to get prices for specified products.
    """
    # Parse arguments
    args = parse_args()
    
    # Setup logging
    if args.debug:
        Config.LOG_LEVEL = 'DEBUG'
    logger = Config.setup_logging()
    
    logger.info(f"Starting Chedraui scraper for products: {', '.join(args.products)}")
    
    try:
        results = {}
        
        # Run API method if selected
        if args.method in ['api', 'both']:
            logger.info("Using GraphQL API method")
            api_scraper = ChedrauiScraper(product_types=args.products, use_api=True)
            
            # Display the search URLs
            print("\nAPI Search URLs:")
            print("-----------")
            for product in args.products:
                search_url = f"{api_scraper.api_url}?query={product}"
                print(f"{product}: {search_url}")
            print()
            
            # Run the API scraper
            api_data = api_scraper.scrape()
            
            if args.method == 'api':
                results = api_data
            else:
                # Store results for later combining
                for product_type, products in api_data.items():
                    results[product_type] = products
        
        # Run HTML method if selected
        if args.method in ['html', 'both']:
            logger.info("Using HTML scraping method")
            html_scraper = ChedrauiScraper(product_types=args.products, use_api=False)
            
            # Display the search URLs
            print("\nHTML Search URLs:")
            print("-----------")
            for product in args.products:
                search_url = f"{html_scraper.base_url}/{product}?_q={product}&map=ft"
                print(f"{product}: {search_url}")
            print()
            
            # Run the HTML scraper
            html_data = html_scraper.scrape()
            
            if args.method == 'html':
                results = html_data
            else:
                # Combine results - add HTML results to existing API results
                for product_type, products in html_data.items():
                    if product_type in results:
                        # Add a marker to show which are from HTML scraping
                        for product in products:
                            product['source'] = 'html'
                        
                        # Only add new products not already found by API
                        existing_ids = set(p.get('product_id', '') for p in results[product_type])
                        for product in products:
                            # If product has no ID or its ID is not in existing products, add it
                            if not product.get('product_id') or product.get('product_id') not in existing_ids:
                                results[product_type].append(product)
                    else:
                        results[product_type] = products
        
        # Save results in all formats or specified format
        scraper = api_scraper if 'api_scraper' in locals() else html_scraper
        
        if args.output == 'all':
            scraper.save_results(results, "json")
            scraper.save_results(results, "csv")
            scraper.save_results(results, "excel")
        else:
            scraper.save_results(results, args.output)
        
        # Print a summary of the results
        print("\nScraping Results Summary:")
        print("--------------------------")
        
        for product_type, products in results.items():
            print(f"\n{product_type.upper()} products found: {len(products)}")
            if products:
                # Group products by source
                api_products = [p for p in products if p.get('source') == 'api']
                html_products = [p for p in products if p.get('source') == 'html']
                other_products = [p for p in products if p.get('source') not in ['api', 'html']]
                
                print(f"  API: {len(api_products)}, HTML: {len(html_products)}, Other: {len(other_products)}")
                
                print("\nTop 5 results:")
                for i, product in enumerate(products[:5]):
                    source = product.get('source', 'unknown')
                    print(f"  {i+1}. {product['name']}: {product['price_text']} (Source: {source})")
        
        print(f"\nData saved to {Config.PROCESSED_DATA_PATH}")
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 