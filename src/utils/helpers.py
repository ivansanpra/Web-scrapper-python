"""
Helper functions for the web scraping project.
"""
import time
import re
import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from bs4 import BeautifulSoup, Tag


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be used as a filename.
    
    Args:
        filename: The string to sanitize
        
    Returns:
        Sanitized filename
    """
    # Replace invalid characters with underscore
    return re.sub(r'[\\/*?:"<>|]', '_', filename)


def save_to_json(data: Union[List, Dict], filepath: Union[str, Path], pretty: bool = True) -> None:
    """
    Save data to a JSON file.
    
    Args:
        data: The data to save
        filepath: Path to the JSON file
        pretty: Whether to format the JSON with indentation
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, ensure_ascii=False)


def save_to_csv(data: List[Dict], filepath: Union[str, Path], headers: Optional[List[str]] = None) -> None:
    """
    Save data to a CSV file.
    
    Args:
        data: List of dictionaries to save
        filepath: Path to the CSV file
        headers: Optional list of headers (uses dict keys if None)
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    if not data:
        return
    
    if headers is None:
        headers = list(data[0].keys())
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)


def save_to_excel(data: Union[List[Dict], pd.DataFrame], filepath: Union[str, Path]) -> None:
    """
    Save data to an Excel file.
    
    Args:
        data: List of dictionaries or DataFrame to save
        filepath: Path to the Excel file
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data
    
    df.to_excel(filepath, index=False)


def extract_text(element: Optional[Tag]) -> str:
    """
    Safely extract text from a BeautifulSoup element.
    
    Args:
        element: BeautifulSoup Tag or None
        
    Returns:
        Extracted text or empty string
    """
    if element is None:
        return ""
    return element.get_text(strip=True)


def extract_attribute(element: Optional[Tag], attribute: str) -> str:
    """
    Safely extract an attribute from a BeautifulSoup element.
    
    Args:
        element: BeautifulSoup Tag or None
        attribute: Name of the attribute to extract
        
    Returns:
        Attribute value or empty string
    """
    if element is None:
        return ""
    return element.get(attribute, "")


def rate_limit(delay: float = 1.0) -> None:
    """
    Sleep for the specified amount of time to respect rate limits.
    
    Args:
        delay: Time to sleep in seconds
    """
    time.sleep(delay) 