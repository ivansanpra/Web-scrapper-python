"""
Chedraui scraper to extract prices for specific products.
"""
import logging
import json
import re
import urllib.parse
from typing import Dict, List, Any, Optional
import time
from pathlib import Path

from src.scrapers.base_scraper import BaseScraper
from src.utils.helpers import extract_text, extract_attribute, rate_limit
from src.utils.config import Config

class ChedrauiScraper(BaseScraper):
    """
    Scraper for Chedraui website to extract product information.
    Can be used for any product type, such as aguacate (avocado), jitomate (tomato), manzana (apple), etc.
    
    Supports both HTML scraping and direct API access using GraphQL.
    """
    
    def __init__(self, base_url: str = "https://www.chedraui.com.mx", headers: Optional[Dict[str, str]] = None, 
                 product_types: Optional[List[str]] = None, use_api: bool = True):
        """
        Initialize the Chedraui scraper.
        
        Args:
            base_url: Base URL for Chedraui website
            headers: Optional HTTP headers for requests
            product_types: Optional list of product types to search for (e.g., ["aguacate", "jitomate", "manzana"])
                           If not provided, defaults to ["aguacate", "jitomate"]
            use_api: Whether to use the GraphQL API (preferred) or fall back to HTML scraping
        """
        # Define enhanced headers that mimic a browser for API requests
        enhanced_headers = {
            'accept': '*/*',
            'accept-language': 'es-419,es;q=0.9',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'referer': f'{base_url}/',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin'
        }
        
        # Override with any provided headers
        if headers:
            enhanced_headers.update(headers)
            
        super().__init__(base_url, enhanced_headers)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Default product types if none provided
        self.product_types = product_types or ["aguacate", "jitomate"]
        self.logger.info(f"Initialized scraper with product types: {self.product_types}")
        
        # API settings
        self.use_api = use_api
        self.api_url = f"{self.base_url}/_v/segment/graphql/v1"
        
    def search_product_api(self, query: str, page_size: int = 20) -> List[Dict[str, Any]]:
        """
        Search for products using the Chedraui GraphQL API.
        
        Args:
            query: Product name to search for
            page_size: Number of results to return (default: 20)
            
        Returns:
            List of product details
        """
        self.logger.info(f"Searching for product via API: {query}")
        
        # Create the API URL with query parameters based on the provided curl example
        params = {
            'workspace': 'master',
            'maxAge': 'short',
            'appsEtag': 'remove',
            'domain': 'store',
            'locale': 'es-MX',
            '__bindingId': 'a3e3947d-516c-4136-ab89-f4a34339bbf4',
            'operationName': 'productSearchV3'
        }
        
        # Construct the variables portion for the GraphQL query
        variables_dict = {
            "hideUnavailableItems": False,
            "skusFilter": "ALL",
            "simulationBehavior": "default",
            "installmentCriteria": "MAX_WITHOUT_INTEREST",
            "productOriginVtex": False,
            "map": "ft",
            "query": query,
            "orderBy": "OrderByScoreDESC",
            "from": 0,
            "to": page_size - 1,
            "selectedFacets": [{"key": "ft", "value": query}],
            "fullText": query,
            "facetsBehavior": "Static",
            "categoryTreeBehavior": "default",
            "withFacets": False,
            "variant": "66844d747af2d50d0f2e2357-variantNull",
            "advertisementOptions": {
                "showSponsored": True,
                "sponsoredCount": 3,
                "advertisementPlacement": "top_search",
                "repeatSponsoredProducts": True
            }
        }
        
        # Encode the variables for the URL
        import base64
        variables_json = json.dumps(variables_dict)
        variables_encoded = base64.b64encode(variables_json.encode('utf-8')).decode('utf-8')
        
        # Construct the extensions portion for the GraphQL query
        extensions_dict = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "9177ba6f883473505dc99fcf2b679a6e270af6320a157f0798b92efeab98d5d3",
                "sender": "vtex.store-resources@0.x",
                "provider": "vtex.search-graphql@0.x"
            },
            "variables": variables_encoded
        }
        
        # Add extensions to parameters
        params['variables'] = '{}'
        params['extensions'] = json.dumps(extensions_dict)
        
        # Build the URL with encoded parameters
        url = self.api_url
        self.logger.info(f"API URL: {url}")
        
        # Add referer header specific to this search
        search_referer = f"{self.base_url}/{query}?_q={query}&map=ft"
        self.session.headers.update({'referer': search_referer})
        
        try:
            # Make the request
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            # Parse the JSON response
            result = response.json()
            
            if 'data' not in result or 'productSearch' not in result['data']:
                self.logger.warning(f"Unexpected API response format: {result}")
                return []
            
            # Extract the product data
            products_data = result['data']['productSearch'].get('products', [])
            self.logger.info(f"Found {len(products_data)} products via API for query: {query}")
            
            # Process the products
            products = []
            for product in products_data:
                try:
                    # Extract basic product information
                    product_id = product.get('productId', '')
                    name = product.get('productName', '')
                    brand = product.get('brand', '')
                    link_id = product.get('linkText', '')
                    
                    # Extract price information
                    price_info = product.get('priceRange', {})
                    selling_price = None
                    list_price = None
                    
                    if price_info and 'sellingPrice' in price_info:
                        selling_price_info = price_info['sellingPrice']
                        if selling_price_info and 'lowPrice' in selling_price_info:
                            selling_price = selling_price_info['lowPrice']
                    
                    if price_info and 'listPrice' in price_info:
                        list_price_info = price_info['listPrice']
                        if list_price_info and 'lowPrice' in list_price_info:
                            list_price = list_price_info['lowPrice']
                    
                    # Format the price text
                    price_text = f"${selling_price}" if selling_price is not None else ""
                    
                    # Extract image URL
                    image_url = ""
                    if 'items' in product and product['items'] and 'images' in product['items'][0]:
                        images = product['items'][0]['images']
                        if images:
                            image_url = images[0].get('imageUrl', '')
                    
                    # Create product URL
                    product_url = f"{self.base_url}/{link_id}/p" if link_id else ""
                    
                    # Add to products list
                    product_data = {
                        "name": name,
                        "brand": brand,
                        "price": selling_price or 0.0,
                        "price_text": price_text,
                        "list_price": list_price,
                        "image_url": image_url,
                        "product_url": product_url,
                        "product_id": product_id,
                        "query": query,
                        "source": "api"
                    }
                    
                    products.append(product_data)
                    self.logger.debug(f"Extracted product via API: {name} - {price_text}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing API product data: {e}")
            
            return products
            
        except Exception as e:
            self.logger.error(f"Error making API request: {e}")
            self.logger.info("Falling back to HTML scraping")
            return []
    
    def parse_sample_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse products from a local HTML sample file.
        This is useful for testing and refining the scraper without making HTTP requests.
        
        Args:
            file_path: Path to the sample HTML file
            
        Returns:
            List of product details
        """
        self.logger.info(f"Parsing sample file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract products using the same logic as search_product
            return self._extract_products(soup, "sample_file")
            
        except Exception as e:
            self.logger.error(f"Error parsing sample file: {e}")
            return []
    
    def search_product(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for a product and extract details.
        If API access is enabled, uses the GraphQL API first, then falls back to HTML scraping if needed.
        
        Args:
            query: Product name to search for
            
        Returns:
            List of product details
        """
        self.logger.info(f"Searching for product: {query}")
        
        # Try API first if enabled
        if self.use_api:
            products = self.search_product_api(query)
            if products:
                return products
            self.logger.warning("API search failed or returned no results, falling back to HTML scraping")
        
        # Fall back to HTML scraping
        search_url = f"{self.base_url}/{query}?_q={query}&map=ft"
        self.logger.info(f"Search URL for HTML scraping: {search_url}")
        
        response = self.get_page(search_url)
        soup = self.parse_html(response)
        
        return self._extract_products(soup, query, search_url)
    
    def _extract_products(self, soup, query: str, url: str = "") -> List[Dict[str, Any]]:
        """
        Extract product information from a BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup object containing the parsed HTML
            query: The search query or identifier
            url: The source URL (optional)
            
        Returns:
            List of product details
        """
        # List to store product data
        products = []
        
        # Find product listing elements - based on the sample HTML
        # First, try the chedrauimx class variant
        product_elements = soup.select("div.chedrauimx-search-result-3-x-galleryItem")
        
        if not product_elements:
            self.logger.warning(f"No products found with chedrauimx class. Trying vtex class.")
            # Try the vtex class variant which is sometimes used
            product_elements = soup.select("div.vtex-search-result-3-x-galleryItem")
            
        if not product_elements:
            self.logger.warning(f"No products found with gallery item selectors. Trying product containers.")
            # Try other container elements
            product_elements = soup.select("section.vtex-product-summary-2-x-container")
            
        self.logger.info(f"Found {len(product_elements)} product elements")
        
        # Extract data from each product
        for product in product_elements:
            try:
                # Extract product details based on the sample HTML structure
                # Product name
                name_elem = product.select_one("span.vtex-product-summary-2-x-productBrand")
                
                # Price - trying multiple selectors based on the HTML structure
                price_elem = None
                price_selectors = [
                    "div.vtex-product-price-1-x-sellingPriceContainer span.vtex-product-price-1-x-currencyContainer",
                    "span.vtex-product-price-1-x-sellingPrice",
                    "div.vtex-product-price-1-x-priceContainer",
                    "div.chedrauimx-product-price-1-x-sellingPriceContainer span"
                ]
                
                for selector in price_selectors:
                    price_elem = product.select_one(selector)
                    if price_elem is not None:
                        break
                
                # Image
                image_elem = product.select_one("img.vtex-product-summary-2-x-imageNormal")
                
                # Product URL
                link_elem = product.select_one("a.vtex-product-summary-2-x-clearLink")
                
                # Extract text and attributes
                name = extract_text(name_elem)
                price_text = extract_text(price_elem)
                price = self.extract_price(price_text)
                image_url = extract_attribute(image_elem, "src")
                product_url = extract_attribute(link_elem, "href")
                
                # Clean URLs if needed
                if product_url and not product_url.startswith("http"):
                    product_url = f"{self.base_url}{product_url}"
                
                # Extract SKU/ID if available
                product_id = ""
                if product_url:
                    import re
                    # Try to extract product ID from URL like /product-name-12345/p
                    match = re.search(r'\/([^\/]+)\/p$', product_url)
                    if match:
                        product_name_with_id = match.group(1)
                        # Try to extract just the ID number
                        id_match = re.search(r'(\d+)$', product_name_with_id)
                        if id_match:
                            product_id = id_match.group(1)
                
                # Add data to products list
                product_data = {
                    "name": name,
                    "price": price,
                    "price_text": price_text,
                    "image_url": image_url,
                    "product_url": product_url,
                    "product_id": product_id,
                    "query": query,
                    "source": "html"
                }
                
                # Only add products with valid names
                if name:
                    products.append(product_data)
                    self.logger.debug(f"Extracted product: {name} - {price_text}")
                
            except Exception as e:
                self.logger.error(f"Error extracting product data: {e}")
        
        # If no products were found with the specific selectors, try to extract using XPath
        if not products:
            self.logger.info("Attempting to extract product information using XPath")
            try:
                # Using lxml for XPath support
                from lxml import html
                
                # Convert soup to string if it's a BeautifulSoup object
                if hasattr(soup, 'prettify'):
                    html_content = soup.prettify()
                else:
                    html_content = str(soup)
                
                # Parse HTML with lxml
                tree = html.fromstring(html_content)
                
                # Use the provided XPath to find price elements
                # XPath: /html/body/div[2]/div/div[1]/div/div[4]/div/div
                price_elements = tree.xpath('/html/body/div[2]/div/div[1]/div/div[4]/div/div')
                self.logger.info(f"Found {len(price_elements)} elements using XPath")
                
                # Additional XPaths for product elements from the sample
                additional_xpaths = [
                    '//div[contains(@class, "chedrauimx-search-result-3-x-galleryItem")]',
                    '//section[contains(@class, "vtex-product-summary-2-x-container")]',
                    '//div[contains(@class, "vtex-product-summary-2-x-element")]'
                ]
                
                for xpath in additional_xpaths:
                    if not price_elements:
                        elements = tree.xpath(xpath)
                        self.logger.info(f"Found {len(elements)} elements using xpath: {xpath}")
                        
                        # Process each element
                        for i, elem in enumerate(elements[:10]):  # Limit to first 10
                            try:
                                # Try to find price
                                price_xpath = './/span[contains(@class, "currencyContainer")]'
                                price_elems = elem.xpath(price_xpath)
                                
                                if price_elems:
                                    price_text = price_elems[0].text_content().strip()
                                    price = self.extract_price(price_text)
                                    
                                    # Try to find name
                                    name_xpath = './/span[contains(@class, "productBrand")]'
                                    name_elems = elem.xpath(name_xpath)
                                    
                                    if name_elems:
                                        name = name_elems[0].text_content().strip()
                                    else:
                                        name = f"{query.capitalize()} {i+1}"
                                    
                                    # Try to find image
                                    img_xpath = './/img'
                                    img_elems = elem.xpath(img_xpath)
                                    image_url = img_elems[0].get('src') if img_elems else ""
                                    
                                    # Try to find link
                                    link_xpath = './/a[contains(@class, "clearLink")]'
                                    link_elems = elem.xpath(link_xpath)
                                    product_url = link_elems[0].get('href') if link_elems else ""
                                    
                                    # Clean URL if needed
                                    if product_url and not product_url.startswith("http"):
                                        product_url = f"{self.base_url}{product_url}"
                                    
                                    product_data = {
                                        "name": name,
                                        "price": price,
                                        "price_text": price_text,
                                        "image_url": image_url,
                                        "product_url": product_url,
                                        "query": query,
                                        "source": "xpath",
                                        "note": f"Extracted using XPath: {xpath}"
                                    }
                                    
                                    products.append(product_data)
                            except Exception as e:
                                self.logger.error(f"Error in XPath extraction for element {i}: {e}")
                
            except ImportError:
                self.logger.warning("lxml not installed, skipping XPath extraction")
            except Exception as e:
                self.logger.error(f"Error during XPath extraction: {e}")
        
        # If still no products found, use the original XPath as last resort
        if not products and 'tree' in locals():
            try:
                price_elements = tree.xpath('/html/body/div[2]/div/div[1]/div/div[4]/div/div')
                self.logger.info(f"Found {len(price_elements)} elements using original XPath")
                
                for i, elem in enumerate(price_elements):
                    try:
                        price_text = elem.text_content().strip() if elem.text_content() else ""
                        if price_text:
                            price = self.extract_price(price_text)
                            name = f"{query.capitalize()} {i+1}"
                            
                            product_data = {
                                "name": name,
                                "price": price,
                                "price_text": price_text,
                                "image_url": "",
                                "product_url": url or "",
                                "query": query,
                                "source": "xpath-original",
                                "note": "Extracted using original XPath"
                            }
                            
                            products.append(product_data)
                    except Exception as e:
                        self.logger.error(f"Error with original XPath for element {i}: {e}")
            except Exception as e:
                self.logger.error(f"Error during original XPath fallback: {e}")
        
        # If still no products found, try the general fallback approach
        if not products:
            self.logger.info("Attempting general fallback extraction for any product information")
            # Look for any price elements on the page
            all_price_elements = soup.select("span.vtex-product-price-1-x-currencyContainer, .price, .product-price")
            for i, price_elem in enumerate(all_price_elements[:10]):  # Limit to first 10 to avoid too much noise
                try:
                    price_text = extract_text(price_elem)
                    price = self.extract_price(price_text)
                    
                    # Try to find a nearby product name
                    parent = price_elem.parent
                    for _ in range(5):  # Look up to 5 levels up
                        if parent:
                            name_elem = parent.select_one(".product-name, .vtex-product-summary-2-x-productBrand, h1, h2, h3")
                            if name_elem:
                                name = extract_text(name_elem)
                                break
                            parent = parent.parent
                        else:
                            break
                    else:
                        name = f"{query.capitalize()} {i+1}"
                    
                    product_data = {
                        "name": name,
                        "price": price,
                        "price_text": price_text,
                        "image_url": "",
                        "product_url": url or "",
                        "query": query,
                        "source": "fallback",
                        "note": "Extracted using general fallback method"
                    }
                    
                    products.append(product_data)
                    
                except Exception as e:
                    self.logger.error(f"Error in fallback extraction: {e}")
        
        self.logger.info(f"Extracted a total of {len(products)} products")
        return products
    
    def extract_price(self, price_text: str) -> float:
        """
        Extract price as a float from price text.
        
        Args:
            price_text: Text containing the price
            
        Returns:
            Float price or 0.0 if extraction fails
        """
        if not price_text:
            return 0.0
        
        try:
            # Remove currency symbol and non-numeric characters except decimal point
            import re
            # First, look for a pattern that matches Mexican peso prices: $123.45
            price_match = re.search(r'\$\s*(\d+(?:[.,]\d+)?)', price_text)
            if price_match:
                price_str = price_match.group(1)
                # Replace comma with dot if used as decimal separator
                cleaned_price = price_str.replace(',', '.')
                return float(cleaned_price)
            else:
                # If no clear pattern, just extract any numeric values
                cleaned_price = re.sub(r'[^\d.]', '', price_text.replace(',', '.'))
                return float(cleaned_price)
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error extracting price from '{price_text}': {e}")
            return 0.0
    
    def scrape(self, product_types: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape product information for specified product types.
        
        Args:
            product_types: Optional list of product types to search for.
                           If provided, overrides the list specified in the constructor.
        
        Returns:
            Dictionary containing product data, keyed by product type
        """
        # Use product_types parameter if provided, otherwise use the instance attribute
        search_terms = product_types or self.product_types
        
        if isinstance(search_terms, str):
            # If a string was passed, convert to a list with a single item
            search_terms = [search_terms]
        
        # Log all URLs that will be searched
        self.logger.info("Starting search with the following products:")
        for term in search_terms:
            search_url = f"{self.base_url}/{term}?_q={term}&map=ft"
            self.logger.info(f" - {term}: {search_url}")
            
        results = {}
        
        for term in search_terms:
            self.logger.info(f"Scraping {term} products")
            products = self.search_product(term)
            results[term] = products
            
            # Respect rate limits between searches
            rate_limit(Config.REQUEST_DELAY)
        
        return results
    
    def scrape_from_sample(self, sample_path: str = "data/sample.html", product_type: str = "sample") -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape product information from a sample HTML file for testing.
        
        Args:
            sample_path: Path to the sample HTML file
            product_type: Key to use for the results dictionary
            
        Returns:
            Dictionary containing product data, keyed by product_type
        """
        self.logger.info(f"Scraping from sample file: {sample_path}")
        products = self.parse_sample_file(sample_path)
        return {product_type: products}
    
    def save_results(self, data: Dict[str, List[Dict[str, Any]]], output_format: str = "json"):
        """
        Save the scraping results to a file.
        
        Args:
            data: The scraped data
            output_format: Format to save the data in (json, csv, excel)
        """
        from src.utils.helpers import save_to_json, save_to_csv, save_to_excel
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"chedraui_products_{timestamp}"
        
        if output_format == "json":
            output_path = Path(Config.PROCESSED_DATA_PATH) / f"{filename}.json"
            save_to_json(data, output_path)
            self.logger.info(f"Results saved to {output_path}")
        
        elif output_format == "csv":
            # Flatten the dictionary to a list for CSV
            flattened_data = []
            for product_type, products in data.items():
                for product in products:
                    product_copy = product.copy()
                    product_copy["product_type"] = product_type
                    flattened_data.append(product_copy)
            
            output_path = Path(Config.PROCESSED_DATA_PATH) / f"{filename}.csv"
            save_to_csv(flattened_data, output_path)
            self.logger.info(f"Results saved to {output_path}")
        
        elif output_format == "excel":
            # Similar flattening for Excel
            flattened_data = []
            for product_type, products in data.items():
                for product in products:
                    product_copy = product.copy()
                    product_copy["product_type"] = product_type
                    flattened_data.append(product_copy)
            
            output_path = Path(Config.PROCESSED_DATA_PATH) / f"{filename}.xlsx"
            save_to_excel(flattened_data, output_path)
            self.logger.info(f"Results saved to {output_path}") 