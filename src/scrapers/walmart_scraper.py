"""
Walmart Mexico scraper to extract prices for specific products.
"""
import logging
import json
import re
import urllib.parse
from typing import Dict, List, Any, Optional
import time
from pathlib import Path
import random
import requests
from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper
from src.utils.helpers import extract_text, extract_attribute, rate_limit
from src.utils.config import Config

class WalmartScraper(BaseScraper):
    """
    Scraper for Walmart Mexico website to extract product information.
    Can be used for any product type, such as platano (banana), manzana (apple), aguacate (avocado), etc.
    
    Uses the Walmart Mexico GraphQL API for efficient and reliable data retrieval.
    """
    
    def __init__(self, base_url: str = "https://super.walmart.com.mx", headers: Optional[Dict[str, str]] = None, 
                 product_types: Optional[List[str]] = None, use_api: bool = True):
        """
        Initialize the Walmart Mexico scraper.
        
        Args:
            base_url: Base URL for Walmart Mexico website
            headers: Optional HTTP headers for requests
            product_types: Optional list of product types to search for (e.g., ["aguacate", "jitomate", "manzana"])
                           If not provided, defaults to ["platano", "manzana", "aguacate"]
            use_api: Whether to use the GraphQL API (preferred) or fall back to HTML scraping
        """
        # Define enhanced headers that mimic a browser for API requests
        enhanced_headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'es-MX,es;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'referer': f'{base_url}/',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-o-bu': 'WALMART-MX',
            'x-o-platform': 'rweb',
            'x-o-segment': 'oaoh',
            'x-o-vertical': 'OD',
            'origin': base_url,
            'dnt': '1',
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'upgrade-insecure-requests': '1'
        }
        
        # Override with any provided headers
        if headers:
            enhanced_headers.update(headers)
            
        super().__init__(base_url, enhanced_headers)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Default product types if none provided
        self.product_types = product_types or ["platano", "manzana", "aguacate"]
        self.logger.info(f"Initialized scraper with product types: {self.product_types}")
        
        # API settings
        self.use_api = use_api
        self.graphql_api_url = f"{self.base_url}/orchestra/graphql/search"
        self.direct_api_url = f"{self.base_url}/api/autocomplete/v2"
        
        # Add default cookies to help bypass anti-bot measures
        self.session.cookies.update({
            'vtex_segment': 'eyJjYW1paG9zdCI6Int9Iiwid29ya3NwYWNlIjoibWFzdGVyIiwiY2hhbm5lbCI6IjEifQ==',
            'WM_QOS.CORRELATION_ID': str(int(time.time() * 1000)),
            '_gcl_au': '1.1.1234567890.1234567890',
            'DYN_USER_ID': str(int(time.time() * 1000))
        })
    
    def make_request(self, url, method='GET', data=None, headers=None, params=None, allow_redirects=True):
        """
        Makes an HTTP request with rate limiting and additional error handling.
        
        Args:
            url: The URL to request
            method: HTTP method (GET, POST, etc.)
            data: Optional data to send (for POST, PUT, etc.)
            headers: Optional headers to add/override for this request
            params: Optional URL parameters
            allow_redirects: Whether to follow redirects
            
        Returns:
            Response object or None if request failed
        """
        custom_headers = self.session.headers.copy()
        if headers:
            custom_headers.update(headers)
            
        # Update referer for each request to make it more realistic
        custom_headers['referer'] = self.base_url + '/search'
        
        # Generate a random 'x-o-correlation-id' header for each request
        custom_headers['x-o-correlation-id'] = f"id-{int(time.time() * 1000)}"
        
        try:
            # Add random delay to mimic human behavior (0.5 to 2 seconds)
            time.sleep(0.5 + (1.5 * random.random()))
            
            # Add rate limiting
            rate_limit(1.5)  # Add a 1.5 second delay between requests
            
            if method.upper() == 'GET':
                response = self.session.get(url, headers=custom_headers, params=params, 
                                        allow_redirects=allow_redirects, timeout=15)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=custom_headers, json=data, params=params,
                                         allow_redirects=allow_redirects, timeout=15)
            else:
                self.logger.error(f"Unsupported HTTP method: {method}")
                return None
                
            # Log response status
            self.logger.debug(f"Request to {url} returned status {response.status_code}")
            
            # Check for common error statuses
            if response.status_code == 403:
                self.logger.error(f"Received 403 Forbidden from {url}. The website may be blocking our requests.")
                return None
            elif response.status_code == 412:
                self.logger.error(f"Received 412 Precondition Failed from {url}. May need to update headers or cookies.")
                return None
            elif response.status_code == 429:
                self.logger.error(f"Received 429 Too Many Requests from {url}. Waiting before retrying...")
                time.sleep(10)  # Wait longer for rate limiting
                return None
                
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None
    
    def search_product_direct_api(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for products using the direct autocomplete API endpoint which is more reliable.
        
        Args:
            query: Product name to search for
            
        Returns:
            List of product details
        """
        self.logger.info(f"Searching for product via direct API: {query}")
        
        # Build the search URL with query parameters
        search_api_url = f"{self.direct_api_url}?term={urllib.parse.quote(query)}&termLimit=10&departmentLimit=2&tenant=OD"
        self.logger.info(f"Direct API URL: {search_api_url}")
        
        # Set referer header for this specific request
        referer_headers = {
            'referer': f"{self.base_url}/search?q={urllib.parse.quote(query)}",
        }
        
        try:
            # Make the request
            response = self.make_request(search_api_url, headers=referer_headers)
            if not response:
                return []
            
            # Parse the JSON response
            result = response.json()
            
            # Debug the response structure
            self.logger.debug(f"Direct API response structure: {type(result)}")
            if isinstance(result, str):
                try:
                    # Try to parse the string as JSON
                    result = json.loads(result)
                except json.JSONDecodeError:
                    self.logger.error(f"Failed to parse direct API response as JSON: {result[:100]}...")
                    return []
            
            # Check if we have results
            products = []
            
            # Handle different response formats
            if isinstance(result, dict) and 'suggestions' in result:
                suggestions = result['suggestions']
                for suggestion in suggestions:
                    try:
                        if 'productId' not in suggestion:
                            continue
                            
                        product_id = suggestion.get('productId', '')
                        name = suggestion.get('displayName', '')
                        
                        # Create product URL
                        product_url = f"{self.base_url}/ip/{product_id}"
                        
                        # Extract price if available
                        price_text = suggestion.get('priceInfo', {}).get('priceString', '')
                        price = 0.0
                        if 'priceInfo' in suggestion and 'price' in suggestion['priceInfo']:
                            try:
                                price = float(suggestion['priceInfo']['price'])
                            except (ValueError, TypeError):
                                pass
                        
                        # Extract image URL if available
                        image_url = suggestion.get('imageUrl', '')
                        
                        # Create product data
                        product_data = {
                            'name': name,
                            'price_text': price_text,
                            'price': price,
                            'product_id': product_id,
                            'url': product_url,
                            'image_url': image_url,
                            'source': 'api-direct',
                            'store': 'Walmart',
                            'query': query
                        }
                        
                        products.append(product_data)
                        self.logger.debug(f"Extracted product via direct API: {name} - {price_text}")
                    except Exception as e:
                        self.logger.error(f"Error processing direct API product data: {e}")
            elif isinstance(result, list):
                # Handle list response format
                for item in result:
                    try:
                        if not isinstance(item, dict):
                            continue
                            
                        # Extract product details
                        name = item.get('term', '')
                        if not name:
                            continue
                            
                        # Create product data with minimal information
                        # We'll need to fetch more details later
                        product_data = {
                            'name': name,
                            'price_text': '',
                            'price': 0.0,
                            'product_id': '',
                            'url': f"{self.base_url}/search?q={urllib.parse.quote(name)}",
                            'image_url': '',
                            'source': 'api-direct-suggestion',
                            'store': 'Walmart',
                            'query': query
                        }
                        
                        products.append(product_data)
                        self.logger.debug(f"Extracted product suggestion via direct API: {name}")
                    except Exception as e:
                        self.logger.error(f"Error processing direct API suggestion data: {e}")
            
            self.logger.info(f"Found {len(products)} products via direct API for query: {query}")
            return products
            
        except Exception as e:
            self.logger.error(f"Error making direct API request: {e}")
            return []
    
    def search_product_graphql_api(self, query: str, page: int = 1, limit: int = 40) -> List[Dict[str, Any]]:
        """
        Search for products using the GraphQL API.
        
        Args:
            query: Product name to search for
            page: Page number for pagination
            limit: Number of results to fetch
            
        Returns:
            List of product details
        """
        self.logger.info(f"Searching for product via GraphQL API: {query}")
        
        # First try direct API which has shown to be more reliable
        direct_results = self.search_product_direct_api(query)
        if direct_results:
            return direct_results
            
        self.logger.info(f"Direct API returned no results, trying GraphQL API...")
        
        # Build the GraphQL API URL
        search_api_url = f"{self.graphql_api_url}?query={urllib.parse.quote(query)}&page={page}&prg=desktop"
        self.logger.info(f"GraphQL API URL: {search_api_url}")
        
        # Prepare the query payload
        graphql_query = {
            "query": "query Search($query: String!, $page: Int, $facets: [String], $sort: String, $affinityOverride: AffinityOverride, $channel: String, $tenant: String, $skipGallery: Boolean! = false) { search(query: $query, page: $page, facets: $facets, sort: $sort, affinityOverride: $affinityOverride, channel: $channel, tenant: $tenant) { query products { ...ProductFragment } __typename } gallery @skip(if: $skipGallery) { layouts(ids: [\"Collection_Gallery_Visual\", \"Collection_Gallery_XL\", \"CMS_MODULE\"]) { id template data { __typename contentType ... on Collection_Gallery_DataType { products { ...ProductFragment } __typename } } __typename } __typename } } fragment ProductFragment on Product { id usItemId sponsoredProduct name canonicalUrl numberOfReviews averageRating availabilityStatus inventory { value displayValue } priceInfo { itemPrice { ... on FormatPrice { priceString price } __typename } wasPrice { ... on FormatPrice { priceString price } __typename } unitPrice { __typename } } badges { flags { __typename id key text } tags { __typename id key text } } imageInfo { thumbnailUrl size { width height } } fulfillmentBadge shelf { name aisleLocator { deep { aisle zone displayName } } } foundAt offerId geoItemClassification { displayValue } productClassification { displayValue } __typename }",
            "variables": {
                "query": query,
                "page": page,
                "sort": "best_match",
                "ps": limit,
                "limit": limit,
                "additionalQueryParams.isMoreOptionsTileEnabled": True,
                "additionalQueryParams.isGenAiEnabled": False,
                "tenant": "MX_GLASS",
                "enableMultiSave": True,
                "enableFacetCount": True,
                "ffAwareSearchOptOut": False,
                "fitmentFieldParams": "true_true_true"
            }
        }
        
        # Set headers specific for this GraphQL request
        graphql_headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'x-apollo-operation-name': 'Search',
            'x-o-platform-version': 'main-1.13.0-0eb8f0',
            'x-o-ccm': 'server',
            'x-o-gql-query': 'query Search'
        }
        
        try:
            # First try with POST request (the proper way)
            response = self.make_request(
                self.graphql_api_url, 
                method='POST',
                data=graphql_query,
                headers=graphql_headers
            )
            
            if not response:
                self.logger.warning("POST request failed, trying with URL parameters")
                # Try with GET request and parameters in URL
                get_params = {
                    "query": query,
                    "page": page,
                    "prg": "desktop",
                    "sort": "best_match",
                    "ps": limit,
                    "limit": limit,
                    "additionalQueryParams.isMoreOptionsTileEnabled": "true",
                    "additionalQueryParams.isGenAiEnabled": "false",
                    "tenant": "MX_GLASS",
                    "enableMultiSave": "true",
                    "enableFacetCount": "true",
                    "ffAwareSearchOptOut": "false",
                    "fitmentFieldParams": "true_true_true"
                }
                response = self.make_request(self.graphql_api_url, params=get_params)
                
            if not response:
                self.logger.error("Both POST and GET requests failed")
                return []
                
            # Parse the JSON response
            result = response.json()
            
            # Extract products from the response
            products = []
            
            if 'data' in result and 'search' in result['data'] and 'products' in result['data']['search']:
                raw_products = result['data']['search']['products']
                
                for product in raw_products:
                    try:
                        # Extract price information
                        price_text = ""
                        price_value = 0.0
                        
                        if ('priceInfo' in product and 'itemPrice' in product['priceInfo'] and 
                            'priceString' in product['priceInfo']['itemPrice']):
                            price_text = product['priceInfo']['itemPrice']['priceString']
                            price_value = float(product['priceInfo']['itemPrice'].get('price', 0))
                        
                        # Extract image URL
                        image_url = product.get('imageInfo', {}).get('thumbnailUrl', '')
                        
                        # Create structured product data
                        product_data = {
                            'name': product.get('name', ''),
                            'price_text': price_text,
                            'price': price_value,
                            'product_id': product.get('id', ''),
                            'usItemId': product.get('usItemId', ''),
                            'url': self.base_url + product.get('canonicalUrl', ''),
                            'image_url': image_url,
                            'source': 'api',
                            'store': 'Walmart',
                            'availability': product.get('availabilityStatus', ''),
                            'rating': product.get('averageRating', 0),
                            'reviews': product.get('numberOfReviews', 0),
                            'category': product.get('shelf', {}).get('name', ''),
                            'raw_data': product  # Store the raw data for debugging
                        }
                        
                        products.append(product_data)
                    except Exception as e:
                        self.logger.error(f"Error parsing product from GraphQL response: {e}")
                        continue
            
            self.logger.info(f"Found {len(products)} products from GraphQL API")
            return products
            
        except Exception as e:
            self.logger.error(f"Error making GraphQL API request: {e}")
            return []
    
    def extract_products_from_search_page(self, query: str) -> List[Dict[str, Any]]:
        """
        Extract products directly from the search results page HTML.
        This is a fallback method when APIs fail.
        
        Args:
            query: Product name to search for
            
        Returns:
            List of product details
        """
        self.logger.info(f"Extracting products from search page for: {query}")
        search_url = f"{self.base_url}/search?q={urllib.parse.quote(query)}"
        
        try:
            # Make the request to the search page
            response = self.make_request(search_url)
            if not response:
                self.logger.error(f"Error fetching {search_url}")
                raise Exception(f"Error fetching {search_url}")
                
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            products = []
            
            # First try to extract embedded JSON data
            try:
                # Look for script tags with embedded JSON data
                script_tags = soup.find_all('script', type='application/json')
                
                for script in script_tags:
                    try:
                        # Parse the JSON content
                        json_data = json.loads(script.string)
                        
                        # Check if this is product data
                        if isinstance(json_data, dict) and 'props' in json_data:
                            props = json_data.get('props', {})
                            page_props = props.get('pageProps', {})
                            
                            # Look for initial state or search results
                            if 'initialState' in page_props:
                                initial_state = page_props.get('initialState', {})
                                search_result = initial_state.get('search', {}).get('searchResult', {})
                                
                                # Extract product items
                                item_stacks = search_result.get('itemStacks', [])
                                for stack in item_stacks:
                                    items = stack.get('items', [])
                                    for item in items:
                                        try:
                                            # Extract basic product information
                                            name = item.get('name', '')
                                            product_id = item.get('usItemId', '')
                                            url_path = item.get('canonicalUrl', '')
                                            
                                            # Extract price information
                                            price_info = item.get('priceInfo', {})
                                            current_price = price_info.get('currentPrice', {})
                                            price = current_price.get('price', 0.0)
                                            price_text = current_price.get('priceString', f"${price}")
                                            
                                            # Extract image URL
                                            image_info = item.get('imageInfo', {})
                                            image_url = image_info.get('thumbnailUrl', '')
                                            
                                            # Create product URL
                                            product_url = f"{self.base_url}{url_path}" if url_path else f"{self.base_url}/ip/{product_id}"
                                            
                                            # Create product data
                                            product_data = {
                                                'name': name,
                                                'price_text': price_text,
                                                'price': price,
                                                'product_id': product_id,
                                                'url': product_url,
                                                'image_url': image_url,
                                                'source': 'search-page-json',
                                                'store': 'Walmart',
                                                'query': query
                                            }
                                            
                                            products.append(product_data)
                                        except Exception as e:
                                            self.logger.error(f"Error processing embedded product data: {e}")
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        self.logger.error(f"Error processing embedded product data: {e}")
            except Exception as e:
                self.logger.error(f"Error processing embedded JSON data: {e}")
            
            # If we didn't get products from embedded JSON, try HTML parsing
            if not products:
                # Try different selectors for product items
                product_selectors = [
                    'div[data-automation-id="product"]',
                    'div.product-card',
                    'div.search-result-gridview-item',
                    'div.Grid-col',
                    'div[data-testid="list-view"]'
                ]
                
                for selector in product_selectors:
                    product_items = soup.select(selector)
                    if product_items:
                        self.logger.info(f"Found {len(product_items)} product items with selector: {selector}")
                        
                        for item in product_items:
                            try:
                                # Try different selectors for product name
                                name_selectors = [
                                    'span[data-automation-id="product-title"]',
                                    'span.product-title-link',
                                    'a.product-title-link',
                                    'div.product-title-link',
                                    'div.product-name'
                                ]
                                
                                name = ""
                                for name_selector in name_selectors:
                                    name_elem = item.select_one(name_selector)
                                    if name_elem:
                                        name = extract_text(name_elem)
                                        break
                                
                                if not name:
                                    # Try finding any link with text
                                    links = item.find_all('a')
                                    for link in links:
                                        if link.text.strip():
                                            name = link.text.strip()
                                            break
                                
                                # Try different selectors for price
                                price_selectors = [
                                    'div[data-automation-id="product-price"]',
                                    'span.price-main',
                                    'div.product-price',
                                    'span.price-characteristic'
                                ]
                                
                                price_text = ""
                                price = 0.0
                                for price_selector in price_selectors:
                                    price_elem = item.select_one(price_selector)
                                    if price_elem:
                                        price_text = extract_text(price_elem)
                                        price = self.extract_price(price_text)
                                        break
                                
                                # Try to extract product URL
                                product_url = ""
                                url_elem = item.find('a')
                                if url_elem and 'href' in url_elem.attrs:
                                    url_path = url_elem['href']
                                    if url_path.startswith('http'):
                                        product_url = url_path
                                    else:
                                        product_url = f"{self.base_url}{url_path}" if url_path.startswith('/') else f"{self.base_url}/{url_path}"
                                
                                # Try to extract product ID from URL
                                product_id = ""
                                if product_url:
                                    # Try to extract ID from URL
                                    id_match = re.search(r'/ip/([^/]+)', product_url)
                                    if id_match:
                                        product_id = id_match.group(1)
                                
                                # Try to extract image URL
                                image_url = ""
                                img_elem = item.find('img')
                                if img_elem and 'src' in img_elem.attrs:
                                    image_url = img_elem['src']
                                elif img_elem and 'data-src' in img_elem.attrs:
                                    image_url = img_elem['data-src']
                                
                                # Only add product if we have at least a name
                                if name:
                                    product_data = {
                                        'name': name,
                                        'price_text': price_text,
                                        'price': price,
                                        'product_id': product_id,
                                        'url': product_url,
                                        'image_url': image_url,
                                        'source': 'search-page-html',
                                        'store': 'Walmart',
                                        'query': query
                                    }
                                    
                                    products.append(product_data)
                            except Exception as e:
                                self.logger.error(f"Error extracting product from HTML: {e}")
                        
                        # If we found products with this selector, break the loop
                        if products:
                            break
            
            self.logger.info(f"Found {len(products)} products from search page for query: {query}")
            return products
            
        except Exception as e:
            self.logger.error(f"Error extracting products from search page: {e}")
            return []
    
    def search_product_html(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for products using HTML scraping as a last resort.
        
        Args:
            query: Product name to search for
            
        Returns:
            List of product details
        """
        self.logger.info(f"Searching for product via HTML: {query}")
        search_url = f"{self.base_url}/search?q={urllib.parse.quote(query)}"
        self.logger.info(f"Search URL for HTML scraping: {search_url}")
        
        try:
            # Make the request to the search page
            response = self.make_request(search_url)
            if not response:
                raise Exception(f"Error fetching {search_url}")
                
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            products = []
            
            # Find product items in search results
            # Try multiple possible selectors for product items
            product_items = soup.select('div[data-automation-id="product"]')
            if not product_items:
                product_items = soup.select('div.product-card')
            if not product_items:
                product_items = soup.select('section.product-card')
            
            if not product_items:
                self.logger.warning("No product items found in HTML response")
                return []
            
            for item in product_items:
                try:
                    # Extract product details
                    # Try multiple possible selectors for the product name
                    name_elem = item.select_one('span[data-automation-id="product-title"]')
                    if not name_elem:
                        name_elem = item.select_one('span.product-title')
                    if not name_elem:
                        name_elem = item.select_one('div.product-title-text')
                    
                    name = extract_text(name_elem)
                    
                    # Extract price - try multiple possible selectors
                    price_elem = item.select_one('div[data-automation-id="price"]')
                    if not price_elem:
                        price_elem = item.select_one('div.product-price')
                    if not price_elem:
                        price_elem = item.select_one('span.price-main')
                    
                    price_text = extract_text(price_elem)
                    price = self.extract_price(price_text)
                    
                    # Extract URL and product ID - try multiple possible selectors
                    link_elem = item.select_one('a[data-automation-id="product-link"]')
                    if not link_elem:
                        link_elem = item.select_one('a.product-link')
                    if not link_elem:
                        link_elem = item.select_one('a')
                    
                    product_url = extract_attribute(link_elem, 'href')
                    if product_url and not product_url.startswith('http'):
                        product_url = f"{self.base_url}{product_url}"
                    
                    # Extract product ID from URL
                    product_id = ""
                    if product_url:
                        product_id_match = re.search(r'/ip/(\d+)', product_url)
                        if product_id_match:
                            product_id = product_id_match.group(1)
                    
                    # Extract image - try multiple possible selectors
                    img_elem = item.select_one('img[data-automation-id="product-image"]')
                    if not img_elem:
                        img_elem = item.select_one('img.product-image')
                    if not img_elem:
                        img_elem = item.select_one('img')
                    
                    image_url = extract_attribute(img_elem, 'src')
                    if not image_url:
                        image_url = extract_attribute(img_elem, 'data-src')
                    
                    # Extract brand - try multiple possible selectors
                    brand = ""
                    brand_elem = item.select_one('span[data-automation-id="product-brand"]')
                    if not brand_elem:
                        brand_elem = item.select_one('span.product-brand')
                    if not brand_elem:
                        brand_elem = item.select_one('div.product-brand')
                    
                    if brand_elem:
                        brand = extract_text(brand_elem)
                    
                    # Try to extract list price (original price) if available
                    list_price = 0.0
                    list_price_elem = item.select_one('span[data-automation-id="was-price"]')
                    if list_price_elem:
                        list_price_text = extract_text(list_price_elem)
                        list_price = self.extract_price(list_price_text)
                    
                    product_data = {
                        "name": name,
                        "brand": brand,
                        "price": price,
                        "price_text": price_text,
                        "list_price": list_price,
                        "image_url": image_url,
                        "product_url": product_url,
                        "product_id": product_id,
                        "query": query,
                        "source": "html"
                    }
                    
                    products.append(product_data)
                    self.logger.debug(f"Extracted product via HTML: {name} - {price_text}")
                    
                except Exception as e:
                    self.logger.error(f"Error extracting product from HTML: {e}")
            
            self.logger.info(f"Found {len(products)} products via HTML for query: {query}")
            return products
            
        except Exception as e:
            self.logger.error(f"Error during HTML search: {e}")
            return []
    
    def search_product(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for products using multiple methods in order of reliability:
        1. Direct API (autocomplete) - Most reliable
        2. GraphQL API - Reliable but may be blocked
        3. Search page data extraction - Fallback for API failures
        4. HTML scraping - Last resort
        
        Args:
            query: Product name to search for
            
        Returns:
            List of product details
        """
        self.logger.info(f"Searching for product: {query}")
        products = []
        
        # Try using the Direct API first (if API is enabled)
        if self.use_api:
            # Try the direct autocomplete API first (most reliable)
            direct_api_products = self.search_product_direct_api(query)
            if direct_api_products:
                self.logger.info(f"Found {len(direct_api_products)} products via Direct API")
                for product in direct_api_products:
                    product['source'] = 'api-direct'
                return direct_api_products
            
            # If direct API fails, try the GraphQL API
            graphql_products = self.search_product_graphql_api(query)
            if graphql_products:
                self.logger.info(f"Found {len(graphql_products)} products via GraphQL API")
                for product in graphql_products:
                    product['source'] = 'api-graphql'
                return graphql_products
            
            # If GraphQL API fails, try extracting from search page data
            search_page_products = self.extract_products_from_search_page(query)
            if search_page_products:
                self.logger.info(f"Found {len(search_page_products)} products via search page extraction")
                for product in search_page_products:
                    product['source'] = 'search-page'
                return search_page_products
            
            self.logger.warning("All API methods failed, falling back to HTML scraping")
        
        # Last resort: HTML scraping
        html_products = self.search_product_html(query)
        if html_products:
            self.logger.info(f"Found {len(html_products)} products via HTML scraping")
            for product in html_products:
                product['source'] = 'html'
            return html_products
        
        self.logger.warning(f"No products found for {query} using any method")
        return []
    
    def extract_price(self, price_text: str) -> float:
        """
        Extract a numeric price from a price string.
        
        Args:
            price_text: Price string to parse, e.g. "$123.45", "MXN $123.45", etc.
            
        Returns:
            Float price value
        """
        try:
            if not price_text:
                return 0.0
            
            # Handle the specific format from Walmart Mexico where price is duplicated
            # Example: "$36.90/kgprecio actual $36.90/kg"
            if "precio actual" in price_text:
                # Split by "precio actual" and take the first part
                price_text = price_text.split("precio actual")[0]
            
            # Remove currency symbols, spaces, and other non-numeric characters
            # Keep only digits, decimal points, and commas
            clean_price = re.sub(r'[^\d.,]', '', price_text)
            
            # Handle Mexican format where comma is used as thousands separator
            # and period as decimal separator
            if ',' in clean_price and '.' in clean_price:
                # If both are present, assume comma is thousands separator
                clean_price = clean_price.replace(',', '')
            elif ',' in clean_price:
                # If only comma is present, it could be a decimal separator (European/Latin American format)
                clean_price = clean_price.replace(',', '.')
            
            # Handle price per kg format
            if '/kg' in price_text:
                self.logger.debug(f"Detected price per kg format: {price_text}")
                # No need to modify the price, just log it
            
            # Handle case where the same price appears twice
            if len(clean_price) > 8 and clean_price[:4] == clean_price[4:8]:
                # This is likely a duplicated price, take just the first occurrence
                clean_price = clean_price[:len(clean_price)//2]
                self.logger.debug(f"Detected duplicated price, using: {clean_price}")
            
            return float(clean_price)
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
            search_url = f"{self.base_url}/search?q={urllib.parse.quote(term)}"
            self.logger.info(f" - {term}: {search_url}")
            
        results = {}
        
        for term in search_terms:
            self.logger.info(f"Scraping {term} products")
            products = self.search_product(term)
            results[term] = products
            
            # Respect rate limits between searches
            rate_limit(Config.REQUEST_DELAY)
        
        return results
    
    def save_results(self, data: Dict[str, List[Dict[str, Any]]], output_format: str = "json"):
        """
        Save the scraped results to a file.
        
        Args:
            data: Dictionary of product data
            output_format: Output format (json, csv, excel, or all)
        """
        from src.utils.helpers import save_to_json, save_to_csv, save_to_excel
        
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_dir = Path(Config.PROCESSED_DATA_PATH) / "walmart"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a flattened list of all products for CSV and Excel formats
        flattened_data = []
        for product_type, products in data.items():
            for product in products:
                product_copy = product.copy()
                if 'query' not in product_copy:
                    product_copy['query'] = product_type
                flattened_data.append(product_copy)
        
        # Save based on specified format
        if output_format.lower() == 'json' or output_format.lower() == 'all':
            json_path = output_dir / f"walmart_products_{timestamp}.json"
            save_to_json(data, json_path)
            self.logger.info(f"Saved JSON results to {json_path}")
            
        if output_format.lower() == 'csv' or output_format.lower() == 'all':
            csv_path = output_dir / f"walmart_products_{timestamp}.csv"
            save_to_csv(flattened_data, csv_path)
            self.logger.info(f"Saved CSV results to {csv_path}")
            
        if output_format.lower() == 'excel' or output_format.lower() == 'all':
            excel_path = output_dir / f"walmart_products_{timestamp}.xlsx"
            save_to_excel(flattened_data, excel_path)
            self.logger.info(f"Saved Excel results to {excel_path}") 