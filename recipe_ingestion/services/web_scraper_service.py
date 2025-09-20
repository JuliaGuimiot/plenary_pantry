"""
Web Scraper Service for URL content extraction.

This service handles all web scraping operations including content extraction,
structured data parsing, and JavaScript-heavy site handling.
"""

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from ..utils.constants import WebScrapingConfig

logger = logging.getLogger(__name__)


class WebScraperService:
    """Service for web scraping and content extraction."""
    
    def __init__(self):
        """Initialize the web scraper service."""
        self.user_agent = WebScrapingConfig.USER_AGENT
        self.request_timeout = WebScrapingConfig.REQUEST_TIMEOUT
        self.selenium_timeout = WebScrapingConfig.SELENIUM_TIMEOUT
        self.max_retries = WebScrapingConfig.MAX_RETRIES
    
    def extract_content_from_url(self, url: str) -> str:
        """
        Extract content from web URL.
        
        Args:
            url: URL to extract content from
            
        Returns:
            Extracted text content
        """
        try:
            # Try with requests first
            content = self._extract_with_requests(url)
            if content:
                return content
        except Exception as e:
            logger.warning(f"Requests extraction failed: {str(e)}")
        
        try:
            # Fall back to Selenium for JavaScript-heavy sites
            content = self._extract_with_selenium(url)
            if content:
                return content
        except Exception as e:
            logger.warning(f"Selenium extraction failed: {str(e)}")
        
        raise Exception(f"Failed to extract content from URL: {url}")
    
    def _extract_with_requests(self, url: str) -> Optional[str]:
        """
        Extract content using requests and BeautifulSoup.
        
        Args:
            url: URL to extract content from
            
        Returns:
            Extracted text content or None if failed
        """
        headers = {'User-Agent': self.user_agent}
        response = requests.get(url, headers=headers, timeout=self.request_timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # First, try to extract structured recipe data (JSON-LD)
        structured_content = self._extract_structured_recipe_data(soup)
        if structured_content:
            return structured_content
        
        # Fall back to HTML parsing
        return self._extract_recipe_from_html(soup)
    
    def _extract_with_selenium(self, url: str) -> Optional[str]:
        """
        Extract content using Selenium for JavaScript-heavy sites.
        
        Args:
            url: URL to extract content from
            
        Returns:
            Extracted text content or None if failed
        """
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=options)
        try:
            driver.get(url)
            WebDriverWait(driver, self.selenium_timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try structured data first
            structured_content = self._extract_structured_recipe_data(soup)
            if structured_content:
                return structured_content
            
            # Fall back to HTML parsing
            return self._extract_recipe_from_html(soup)
            
        finally:
            driver.quit()
    
    def _extract_structured_recipe_data(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract recipe data from JSON-LD structured data.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Formatted recipe text or None if no structured data found
        """
        try:
            # Look for JSON-LD script tags
            json_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    
                    # Handle both single objects and arrays
                    if isinstance(data, list):
                        for item in data:
                            if self._is_recipe_data(item):
                                return self._format_structured_recipe(item)
                    elif self._is_recipe_data(data):
                        return self._format_structured_recipe(data)
                        
                except (json.JSONDecodeError, KeyError):
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Structured data extraction failed: {str(e)}")
            return None
    
    def _is_recipe_data(self, data: dict) -> bool:
        """Check if JSON-LD data represents a recipe."""
        return (
            data.get('@type') == 'Recipe' or
            'Recipe' in str(data.get('@type', ''))
        )
    
    def _format_structured_recipe(self, recipe_data: dict) -> str:
        """
        Format structured recipe data into readable text.
        
        Args:
            recipe_data: Recipe data from JSON-LD
            
        Returns:
            Formatted recipe text
        """
        lines = []
        
        # Recipe name
        name = recipe_data.get('name', '')
        if name:
            lines.append(f"Recipe: {name}")
            lines.append("=" * (len(name) + 9))
            lines.append("")
        
        # Description
        description = recipe_data.get('description', '')
        if description:
            lines.append(f"Description: {description}")
            lines.append("")
        
        # Ingredients
        ingredients = recipe_data.get('recipeIngredient', [])
        if ingredients:
            lines.append("INGREDIENTS:")
            for ingredient in ingredients:
                lines.append(f"• {ingredient}")
            lines.append("")
        
        # Instructions
        instructions = recipe_data.get('recipeInstructions', [])
        if instructions:
            lines.append("INSTRUCTIONS:")
            for i, instruction in enumerate(instructions, 1):
                if isinstance(instruction, dict):
                    text = instruction.get('text', '')
                else:
                    text = str(instruction)
                lines.append(f"{i}. {text}")
            lines.append("")
        
        # Cook time
        cook_time = recipe_data.get('cookTime', '')
        if cook_time:
            lines.append(f"Cook Time: {cook_time}")
        
        # Prep time
        prep_time = recipe_data.get('prepTime', '')
        if prep_time:
            lines.append(f"Prep Time: {prep_time}")
        
        # Total time
        total_time = recipe_data.get('totalTime', '')
        if total_time:
            lines.append(f"Total Time: {total_time}")
        
        # Servings
        recipe_yield = recipe_data.get('recipeYield', '')
        if recipe_yield:
            lines.append(f"Serves: {recipe_yield}")
        
        return '\n'.join(lines)
    
    def _extract_recipe_from_html(self, soup: BeautifulSoup) -> str:
        """
        Extract recipe from common HTML patterns.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Extracted recipe text
        """
        lines = []
        
        # Try to find recipe title
        title_selectors = [
            'h1[class*="recipe"]', 'h1[class*="title"]',
            '.recipe-title', '.recipe-name', 'h1'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                lines.append(f"Recipe: {title_elem.get_text().strip()}")
                lines.append("=" * (len(title_elem.get_text().strip()) + 9))
                lines.append("")
                break
        
        # Try to find ingredients
        ingredients_selectors = [
            '[class*="ingredient"]', '[class*="ingredients"]',
            '.recipe-ingredients', '.ingredients-list'
        ]
        
        for selector in ingredients_selectors:
            ingredients_elem = soup.select_one(selector)
            if ingredients_elem:
                lines.append("INGREDIENTS:")
                for item in ingredients_elem.find_all(['li', 'span', 'div']):
                    text = item.get_text().strip()
                    if text and len(text) > 2:
                        lines.append(f"• {text}")
                lines.append("")
                break
        
        # Try to find instructions
        instructions_selectors = [
            '[class*="instruction"]', '[class*="instructions"]',
            '[class*="direction"]', '[class*="directions"]',
            '.recipe-instructions', '.instructions-list'
        ]
        
        for selector in instructions_selectors:
            instructions_elem = soup.select_one(selector)
            if instructions_elem:
                lines.append("INSTRUCTIONS:")
                for i, item in enumerate(instructions_elem.find_all(['li', 'p', 'div']), 1):
                    text = item.get_text().strip()
                    if text and len(text) > 10:
                        lines.append(f"{i}. {text}")
                lines.append("")
                break
        
        # If no structured content found, extract general text
        if not lines:
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get main content
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            if main_content:
                text = main_content.get_text()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        return '\n'.join(lines)
    
    def get_page_title(self, url: str) -> Optional[str]:
        """
        Get the page title from a URL.
        
        Args:
            url: URL to get title from
            
        Returns:
            Page title or None if failed
        """
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=self.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            title_tag = soup.find('title')
            
            return title_tag.get_text().strip() if title_tag else None
            
        except Exception as e:
            logger.warning(f"Could not get page title: {str(e)}")
            return None
