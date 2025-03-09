# Web Scraper Project

A flexible and extensible web scraping framework built in Python.

## Features

- Modular design for adding new scrapers
- Rate limiting to prevent overloading target websites
- Configurable output formats (JSON, CSV, Excel)
- Logging system for monitoring and debugging
- Environment-based configuration
- Helper utilities for common scraping tasks
- Unit tests for key components

## Project Structure

```
web_scraper/
│
├── src/                # Source code
│   ├── scrapers/       # Scraper implementations
│   ├── utils/          # Utility functions
│   └── main.py         # Entry point
│
├── data/               # Data storage
│   ├── raw/            # Raw scraped data
│   └── processed/      # Processed data
│
├── tests/              # Unit tests
│   └── test_scrapers/  # Tests for scrapers
│
├── logs/               # Log files
│
├── myenv/              # Virtual environment (not tracked in git)
├── requirements.txt    # Project dependencies
├── .env                # Environment variables (not tracked in git)
├── .gitignore          # Git ignore file
└── README.md           # Project documentation
```

## Setup

### Prerequisites

- Python 3.7+
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/web_scraper.git
cd web_scraper
```

2. Activate the virtual environment:
```bash
# Using cmd.exe (Windows)
myenv\Scripts\activate.bat

# Using PowerShell (Windows) - may require execution policy change
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\myenv\Scripts\Activate.ps1

# Using bash (Linux/Mac)
source myenv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables by editing the `.env` file.

## Usage

### Running the scraper

```bash
# Run all scrapers
python -m src.main

# Run a specific scraper
python -m src.main --target example

# Run with debug logging
python -m src.main --debug

# Specify output format
python -m src.main --output csv
```

### Adding a new scraper

1. Create a new file in the `src/scrapers` directory:
```python
# src/scrapers/my_scraper.py
from src.scrapers.base_scraper import BaseScraper

class MyScraper(BaseScraper):
    def __init__(self, base_url="https://example.com"):
        super().__init__(base_url)
    
    def scrape(self):
        # Implement scraping logic
        response = self.get_page(self.base_url)
        soup = self.parse_html(response)
        
        # Extract data
        data = []
        # ... scraping code ...
        
        return self.clean_data(data)
    
    def clean_data(self, data):
        # Implement data cleaning/processing
        return data
```

2. Update the main script to include your new scraper:
```python
# In src/main.py
from src.scrapers.my_scraper import MyScraper

# Add your scraper to the choices
parser.add_argument(
    '--target',
    type=str,
    choices=['all', 'example', 'my_scraper'],
    default='all',
    help='Scraper target to run'
)

# Add handling for your scraper
elif args.target == 'my_scraper':
    logger.info("Running my scraper")
    scraper = MyScraper()
    # ... rest of the code ...
```

## Best Practices

- Always respect the website's `robots.txt` file
- Implement rate limiting to avoid overloading the target website
- Be careful with how you handle and store scraped data
- Add proper error handling to deal with unexpected HTML structures
- Write tests for your scrapers to ensure they work as expected

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request 