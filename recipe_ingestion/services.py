import re
import json
import logging
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime

import pytesseract
from PIL import Image
import cv2
import numpy as np
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from django.db import transaction
from django.conf import settings
from django.core.files import File

from .models import (
    IngestionSource, IngestionJob, ExtractedRecipe, 
    IngredientMapping, ProcessingLog, RecipeTemplate
)
from core.models import (
    Recipe, RecipeIngredient, Ingredient, Unit, 
    Difficulty, Cuisine, Course, Diet
)

logger = logging.getLogger(__name__)


class RecipeIngestionService:
    """Main service for recipe ingestion and processing"""
    
    def __init__(self, user):
        self.user = user
        self.ingredient_normalizer = IngredientNormalizer()
        self.recipe_parser = RecipeParser()
    
    def process_source(self, source: IngestionSource) -> IngestionJob:
        """Process a recipe source and create a job"""
        job = IngestionJob.objects.create(source=source)
        
        try:
            self._log(job, "Starting processing", "info")
            
            if source.source_type == 'image':
                self._process_image_source(job, source)
            elif source.source_type == 'multi_image':
                self._process_multi_image_source(job, source)
            elif source.source_type == 'url':
                self._process_url_source(job, source)
            elif source.source_type == 'text':
                self._process_text_source(job, source)
            elif source.source_type == 'email':
                self._process_email_source(job, source)
            else:
                raise ValueError(f"Unsupported source type: {source.source_type}")
            
            job.status = 'completed'
            job.completed_at = datetime.now()
            job.save()
            
            self._log(job, "Processing completed successfully", "info")
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            self._log(job, f"Processing failed: {str(e)}", "error")
            logger.error(f"Recipe ingestion failed: {str(e)}", exc_info=True)
        
        return job
    
    def _process_image_source(self, job: IngestionJob, source: IngestionSource):
        """Process image sources using OCR"""
        self._log(job, "Processing image with OCR", "info")
        
        # Extract text using OCR
        image_path = source.source_file.path
        extracted_text = self._extract_text_from_image(image_path)
        
        # Update source with extracted text
        source.raw_text = extracted_text
        source.processed_at = datetime.now()
        source.save()
        
        # Parse recipes from extracted text
        recipes = self.recipe_parser.parse_recipes_from_text(extracted_text)
        
        # Create extracted recipe records
        for recipe_data in recipes:
            ExtractedRecipe.objects.create(
                job=job,
                raw_name=recipe_data.get('name', ''),
                raw_instructions=recipe_data.get('instructions', ''),
                raw_ingredients=recipe_data.get('ingredients', []),
                raw_metadata=recipe_data.get('metadata', {}),
                confidence_score=recipe_data.get('confidence', 0.0)
            )
        
        job.recipes_found = len(recipes)
        job.recipes_processed = len(recipes)
        job.save()
        
        self._log(job, f"Extracted {len(recipes)} recipes from image", "info")
    
    def _process_multi_image_source(self, job: IngestionJob, source: IngestionSource):
        """Process multi-image sources"""
        self._log(job, f"Processing multi-image source with {source.multi_images.count()} images", "info")
        
        # Get all images ordered by page number
        multi_images = source.multi_images.all().order_by('page_number')
        
        if not multi_images.exists():
            raise ValueError("No images found in multi-image source")
        
        # Extract text from all images
        all_text = []
        for multi_image in multi_images:
            try:
                # Extract text from this image
                image_path = multi_image.image_file.path
                extracted_text = self._extract_text_from_image(image_path)
                
                # Store extracted text
                multi_image.extracted_text = extracted_text
                multi_image.save()
                
                # Add to combined text
                all_text.append(f"=== PAGE {multi_image.page_number} ({multi_image.get_page_type_display()}) ===\n")
                all_text.append(extracted_text)
                all_text.append("\n\n")
                
                self._log(job, f"Extracted text from page {multi_image.page_number}", "info")
                
            except Exception as e:
                self._log(job, f"Failed to process page {multi_image.page_number}: {str(e)}", "error")
                continue
        
        # Combine all text
        combined_text = "".join(all_text)
        
        # Update source with combined text
        source.raw_text = combined_text
        source.processed_at = datetime.now()
        source.save()
        
        # Clean up the combined text for better parsing
        cleaned_text = self._clean_multi_image_text(combined_text)
        
        # Parse recipes from cleaned text
        recipes = self.recipe_parser.parse_recipes_from_text(cleaned_text)
        
        # Create extracted recipe records
        for recipe_data in recipes:
            ExtractedRecipe.objects.create(
                job=job,
                raw_name=recipe_data.get('name', ''),
                raw_instructions=recipe_data.get('instructions', ''),
                raw_ingredients=recipe_data.get('ingredients', []),
                raw_metadata=recipe_data.get('metadata', {}),
                confidence_score=recipe_data.get('confidence', 0.0)
            )
        
        job.recipes_found = len(recipes)
        job.recipes_processed = len(recipes)
        job.save()
        
        self._log(job, f"Extracted {len(recipes)} recipes from {len(multi_images)} images", "info")
    
    def _clean_multi_image_text(self, text: str) -> str:
        """Clean up text from multi-image sources for better parsing"""
        import re
        
        # Remove page headers
        text = re.sub(r'=== PAGE \d+ \([^)]+\) ===\n', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # Clean up the text
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('==='):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _process_url_source(self, job: IngestionJob, source: IngestionSource):
        """Process web URL sources"""
        self._log(job, f"Processing URL: {source.source_url}", "info")
        
        # Extract content from URL
        content = self._extract_content_from_url(source.source_url)
        
        # Update source with extracted content
        source.raw_text = content
        source.processed_at = datetime.now()
        source.save()
        
        # Parse recipes from content
        recipes = self.recipe_parser.parse_recipes_from_text(content)
        
        # Create extracted recipe records
        for recipe_data in recipes:
            ExtractedRecipe.objects.create(
                job=job,
                raw_name=recipe_data.get('name', ''),
                raw_instructions=recipe_data.get('instructions', ''),
                raw_ingredients=recipe_data.get('ingredients', []),
                raw_metadata=recipe_data.get('metadata', {}),
                confidence_score=recipe_data.get('confidence', 0.0)
            )
        
        job.recipes_found = len(recipes)
        job.recipes_processed = len(recipes)
        job.save()
        
        self._log(job, f"Extracted {len(recipes)} recipes from URL", "info")
    
    def _process_text_source(self, job: IngestionJob, source: IngestionSource):
        """Process manual text input"""
        self._log(job, "Processing manual text input", "info")
        
        # Parse recipes from raw text
        recipes = self.recipe_parser.parse_recipes_from_text(source.raw_text)
        
        # Create extracted recipe records
        for recipe_data in recipes:
            ExtractedRecipe.objects.create(
                job=job,
                raw_name=recipe_data.get('name', ''),
                raw_instructions=recipe_data.get('instructions', ''),
                raw_ingredients=recipe_data.get('ingredients', []),
                raw_metadata=recipe_data.get('metadata', {}),
                confidence_score=recipe_data.get('confidence', 0.0)
            )
        
        job.recipes_found = len(recipes)
        job.recipes_processed = len(recipes)
        job.save()
        
        self._log(job, f"Extracted {len(recipes)} recipes from text", "info")
    
    def _process_email_source(self, job: IngestionJob, source: IngestionSource):
        """Process email sources with attachments"""
        self._log(job, "Processing email source with attachments", "info")
        
        # Get email details
        try:
            from .models import EmailIngestionSource
            email_source = source.email_details.first()
            if not email_source:
                raise ValueError("No email details found for email source")
            
            # Process each attachment
            total_recipes = 0
            for attachment in email_source.attachments.all():
                if attachment.is_processed:
                    continue
                
                try:
                    # Create temporary source for this attachment
                    temp_source = IngestionSource.objects.create(
                        user=source.user,
                        source_type='image',
                        source_name=f"Email attachment: {attachment.filename}",
                        source_file=attachment.attachment_file
                    )
                    
                    # Process the attachment
                    temp_job = self.process_source(temp_source)
                    
                    # Mark attachment as processed
                    attachment.is_processed = True
                    attachment.save()
                    
                    total_recipes += temp_job.recipes_found
                    
                    self._log(job, f"Processed attachment: {attachment.filename}", "info")
                    
                except Exception as e:
                    self._log(job, f"Failed to process attachment {attachment.filename}: {str(e)}", "error")
                    attachment.processing_error = str(e)
                    attachment.save()
                    continue
            
            job.recipes_found = total_recipes
            job.recipes_processed = total_recipes
            job.save()
            
            self._log(job, f"Processed {total_recipes} recipes from email attachments", "info")
            
        except Exception as e:
            self._log(job, f"Email processing failed: {str(e)}", "error")
            raise
    
    def _extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            # Preprocess image for better OCR
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply preprocessing techniques
            # 1. Noise reduction
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # 2. Thresholding
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 3. Morphological operations
            kernel = np.ones((1, 1), np.uint8)
            processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(processed)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            raise
    
    def _extract_content_from_url(self, url: str) -> str:
        """Extract content from web URL"""
        try:
            # Try with requests first
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # First, try to extract structured recipe data (JSON-LD)
            structured_data = self._extract_structured_recipe_data(soup)
            if structured_data:
                return structured_data
            
            # Try to extract recipe from common recipe website patterns
            recipe_content = self._extract_recipe_from_html(soup)
            if recipe_content:
                return recipe_content
            
            # Fallback to general text extraction
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.error(f"URL content extraction failed: {str(e)}")
            # Fallback to Selenium for JavaScript-heavy sites
            return self._extract_content_with_selenium(url)
    
    def _extract_structured_recipe_data(self, soup: BeautifulSoup) -> str:
        """Extract recipe data from JSON-LD structured data"""
        try:
            # Look for JSON-LD script tags
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'Recipe':
                        return self._format_structured_recipe(data)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'Recipe':
                                return self._format_structured_recipe(item)
                except (json.JSONDecodeError, AttributeError):
                    continue
            return None
        except Exception as e:
            logger.error(f"Structured data extraction failed: {str(e)}")
            return None
    
    def _format_structured_recipe(self, recipe_data: dict) -> str:
        """Format structured recipe data into text"""
        lines = []
        
        # Recipe name
        name = recipe_data.get('name', '')
        if name:
            lines.append(name)
            lines.append('')
        
        # Description
        description = recipe_data.get('description', '')
        if description:
            lines.append(description)
            lines.append('')
        
        # Ingredients
        ingredients = recipe_data.get('recipeIngredient', [])
        if ingredients:
            lines.append('Ingredients:')
            for ingredient in ingredients:
                lines.append(f'• {ingredient}')
            lines.append('')
        
        # Instructions
        instructions = recipe_data.get('recipeInstructions', [])
        if instructions:
            lines.append('Instructions:')
            if isinstance(instructions, list):
                for i, instruction in enumerate(instructions, 1):
                    if isinstance(instruction, dict):
                        instruction_text = instruction.get('text', '')
                    else:
                        instruction_text = str(instruction)
                    lines.append(f'{i}. {instruction_text}')
            else:
                lines.append(instructions)
            lines.append('')
        
        # Additional metadata
        prep_time = recipe_data.get('prepTime', '')
        cook_time = recipe_data.get('cookTime', '')
        total_time = recipe_data.get('totalTime', '')
        servings = recipe_data.get('recipeYield', '')
        
        if prep_time or cook_time or total_time or servings:
            lines.append('Additional Information:')
            if prep_time:
                lines.append(f'Prep Time: {prep_time}')
            if cook_time:
                lines.append(f'Cook Time: {cook_time}')
            if total_time:
                lines.append(f'Total Time: {total_time}')
            if servings:
                lines.append(f'Servings: {servings}')
        
        return '\n'.join(lines)
    
    def _extract_recipe_from_html(self, soup: BeautifulSoup) -> str:
        """Extract recipe from common HTML patterns"""
        lines = []
        
        # Common recipe title selectors
        title_selectors = [
            'h1.recipe-title',
            '.recipe-title h1',
            'h1[class*="recipe"]',
            '.wprm-recipe-name',
            '.recipe-name',
            'h1',
        ]
        
        title = None
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text().strip():
                title = title_elem.get_text().strip()
                break
        
        if title:
            lines.append(title)
            lines.append('')
        
        # Common ingredients selectors
        ingredients_selectors = [
            '.wprm-recipe-ingredients',
            '.recipe-ingredients',
            '.ingredients',
            '[class*="ingredient"]',
            'ul.ingredients',
            'ol.ingredients',
        ]
        
        ingredients_found = False
        for selector in ingredients_selectors:
            ingredients_elem = soup.select_one(selector)
            if ingredients_elem:
                ingredients = []
                for item in ingredients_elem.find_all(['li', 'span', 'div']):
                    text = item.get_text().strip()
                    if text and len(text) > 2:
                        ingredients.append(text)
                
                if ingredients:
                    lines.append('Ingredients:')
                    for ingredient in ingredients:
                        lines.append(f'• {ingredient}')
                    lines.append('')
                    ingredients_found = True
                    break
        
        # Common instructions selectors
        instructions_selectors = [
            '.wprm-recipe-instructions',
            '.recipe-instructions',
            '.instructions',
            '[class*="instruction"]',
            '.directions',
            '.method',
        ]
        
        for selector in instructions_selectors:
            instructions_elem = soup.select_one(selector)
            if instructions_elem:
                instructions = []
                for item in instructions_elem.find_all(['li', 'p', 'div']):
                    text = item.get_text().strip()
                    if text and len(text) > 10:
                        instructions.append(text)
                
                if instructions:
                    lines.append('Instructions:')
                    for i, instruction in enumerate(instructions, 1):
                        lines.append(f'{i}. {instruction}')
                    lines.append('')
                    break
        
        # If we found meaningful content, return it
        if len(lines) > 2:
            return '\n'.join(lines)
        
        return None
    
    def _extract_content_with_selenium(self, url: str) -> str:
        """Extract content using Selenium for JavaScript-heavy sites"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=options)
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        finally:
            driver.quit()
    
    def _log(self, job: IngestionJob, message: str, level: str = 'info'):
        """Log processing steps"""
        ProcessingLog.objects.create(
            job=job,
            step='processing',
            message=message,
            level=level
        )
    
    @transaction.atomic
    def normalize_and_save_recipes(self, job: IngestionJob) -> List[Recipe]:
        """Normalize extracted recipes and save them to the database"""
        self._log(job, "Starting recipe normalization", "info")
        
        saved_recipes = []
        
        for extracted_recipe in job.extracted_recipes.all():
            try:
                # Normalize recipe data
                normalized_recipe = self._normalize_recipe(extracted_recipe)
                
                # Get source information from the ingestion source
                source_info = self._get_source_info(job.source)
                
                # Check for duplicates (same name, source, and user)
                existing_recipe = self._check_for_duplicate_recipe(normalized_recipe, source_info)
                if existing_recipe:
                    self._log(job, f"Duplicate recipe found: {normalized_recipe['name']} from {source_info['name']} (ID: {existing_recipe.id})", "warning")
                    # Update existing recipe if it has fewer ingredients
                    if len(normalized_recipe['ingredients']) > existing_recipe.ingredients.count():
                        self._log(job, f"Updating existing recipe with more ingredients", "info")
                        existing_recipe = self._update_recipe_with_better_data(existing_recipe, normalized_recipe)
                    saved_recipes.append(existing_recipe)
                    continue
                
                # Save recipe with source information
                recipe = Recipe.objects.create(
                    name=normalized_recipe['name'],
                    description=normalized_recipe.get('description', ''),
                    instructions=normalized_recipe['instructions'],
                    prep_time=normalized_recipe.get('prep_time', 0),
                    cook_time=normalized_recipe.get('cook_time', 0),
                    servings=normalized_recipe.get('servings', 1),
                    difficulty=normalized_recipe.get('difficulty'),
                    cuisine=normalized_recipe.get('cuisine'),
                    course=normalized_recipe.get('course'),
                    diet=normalized_recipe.get('diet'),
                    source_name=source_info['name'],
                    source_url=source_info['url'],
                    source_type=source_info['type'],
                    created_by=self.user
                )
                
                # Save ingredients
                for ingredient_data in normalized_recipe['ingredients']:
                    # Skip ingredients without quantities or ingredients
                    if not ingredient_data.get('ingredient') or not ingredient_data.get('quantity'):
                        continue
                    
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        ingredient=ingredient_data['ingredient'],
                        quantity=ingredient_data['quantity'],
                        unit=ingredient_data.get('unit'),
                        preparation_method=ingredient_data.get('preparation_method', '')
                    )
                
                saved_recipes.append(recipe)
                self._log(job, f"Saved recipe: {recipe.name}", "info")
                
            except Exception as e:
                self._log(job, f"Failed to save recipe {extracted_recipe.raw_name}: {str(e)}", "error")
                continue
        
        self._log(job, f"Successfully saved {len(saved_recipes)} recipes", "info")
        return saved_recipes
    
    def _normalize_recipe(self, extracted_recipe: ExtractedRecipe) -> Dict:
        """Normalize extracted recipe data"""
        # Normalize ingredients
        normalized_ingredients = []
        for raw_ingredient in extracted_recipe.raw_ingredients:
            normalized = self.ingredient_normalizer.normalize_ingredient(raw_ingredient)
            if normalized:
                normalized_ingredients.append(normalized)
        
        # Parse recipe metadata
        metadata = extracted_recipe.raw_metadata or {}
        
        return {
            'name': extracted_recipe.raw_name,
            'description': metadata.get('description', ''),
            'instructions': extracted_recipe.raw_instructions,
            'prep_time': metadata.get('prep_time', 0),
            'cook_time': metadata.get('cook_time', 0),
            'servings': metadata.get('servings', 1),
            'difficulty': self._get_or_create_difficulty(metadata.get('difficulty')),
            'cuisine': self._get_or_create_cuisine(metadata.get('cuisine')),
            'course': self._get_or_create_course(metadata.get('course')),
            'diet': self._get_or_create_diet(metadata.get('diet')),
            'ingredients': normalized_ingredients
        }
    
    def _get_or_create_difficulty(self, name: str) -> Optional[Difficulty]:
        if not name:
            return None
        difficulty, _ = Difficulty.objects.get_or_create(name=name.lower())
        return difficulty
    
    def _get_or_create_cuisine(self, name: str) -> Optional[Cuisine]:
        if not name:
            return None
        cuisine, _ = Cuisine.objects.get_or_create(name=name.lower())
        return cuisine
    
    def _get_or_create_course(self, name: str) -> Optional[Course]:
        if not name:
            return None
        course, _ = Course.objects.get_or_create(name=name.lower())
        return course
    
    def _get_or_create_diet(self, name: str) -> Optional[Diet]:
        if not name:
            return None
        diet, _ = Diet.objects.get_or_create(name=name.lower())
        return diet
    
    def _get_source_info(self, source: IngestionSource) -> Dict[str, str]:
        """Extract source information from ingestion source"""
        source_info = {
            'name': source.source_name,
            'url': source.source_url or '',
            'type': source.source_type
        }
        
        # Enhance source name based on type
        if source.source_type == 'url' and source.source_url:
            # Extract domain name from URL
            from urllib.parse import urlparse
            parsed = urlparse(source.source_url)
            domain = parsed.netloc.replace('www.', '')
            if domain and domain not in source.source_name.lower():
                source_info['name'] = f"{source.source_name} ({domain})"
        elif source.source_type == 'image':
            source_info['name'] = f"{source.source_name} (Image Upload)"
        elif source.source_type == 'multi_image':
            source_info['name'] = f"{source.source_name} (Multi-Image Upload)"
        
        return source_info
    
    def _check_for_duplicate_recipe(self, normalized_recipe: Dict, source_info: Dict) -> Optional[Recipe]:
        """Check if a recipe with the same name, source, and user already exists"""
        try:
            existing_recipe = Recipe.objects.get(
                name=normalized_recipe['name'],
                source_name=source_info['name'],
                created_by=self.user
            )
            return existing_recipe
        except Recipe.DoesNotExist:
            return None
    
    def _update_recipe_with_better_data(self, existing_recipe: Recipe, normalized_recipe: Dict) -> Recipe:
        """Update existing recipe with better data (more ingredients, etc.)"""
        # Update basic fields if they're empty or better
        if not existing_recipe.description and normalized_recipe.get('description'):
            existing_recipe.description = normalized_recipe['description']
        
        if not existing_recipe.instructions or len(normalized_recipe['instructions']) > len(existing_recipe.instructions):
            existing_recipe.instructions = normalized_recipe['instructions']
        
        if not existing_recipe.prep_time and normalized_recipe.get('prep_time'):
            existing_recipe.prep_time = normalized_recipe['prep_time']
        
        if not existing_recipe.cook_time and normalized_recipe.get('cook_time'):
            existing_recipe.cook_time = normalized_recipe['cook_time']
        
        if not existing_recipe.servings and normalized_recipe.get('servings'):
            existing_recipe.servings = normalized_recipe['servings']
        
        # Update relationships if not set
        if not existing_recipe.difficulty and normalized_recipe.get('difficulty'):
            existing_recipe.difficulty = normalized_recipe['difficulty']
        
        if not existing_recipe.cuisine and normalized_recipe.get('cuisine'):
            existing_recipe.cuisine = normalized_recipe['cuisine']
        
        if not existing_recipe.course and normalized_recipe.get('course'):
            existing_recipe.course = normalized_recipe['course']
        
        if not existing_recipe.diet and normalized_recipe.get('diet'):
            existing_recipe.diet = normalized_recipe['diet']
        
        existing_recipe.save()
        
        # Add new ingredients if they don't exist
        existing_ingredient_names = set(existing_recipe.ingredients.values_list('ingredient__name', flat=True))
        
        for ingredient_data in normalized_recipe['ingredients']:
            if ingredient_data['ingredient'].name not in existing_ingredient_names:
                RecipeIngredient.objects.create(
                    recipe=existing_recipe,
                    ingredient=ingredient_data['ingredient'],
                    quantity=ingredient_data['quantity'],
                    unit=ingredient_data.get('unit'),
                    preparation_method=ingredient_data.get('preparation_method', '')
                )
        
        return existing_recipe


class IngredientNormalizer:
    """Normalize ingredient text to structured data"""
    
    def __init__(self):
        self.quantity_patterns = [
            # Most specific patterns first
            r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(cups|tablespoons|teaspoons|ounces|pounds|grams|kilograms|milliliters|liters|tbsp|tsp|oz|lb|g|kg|ml|l)',  # Handle ranges - plurals first
            r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(cup|tablespoon|teaspoon|ounce|pound|gram|kilogram|milliliter|liter)',  # Handle ranges - singulars
            r'(\d+(?:\.\d+)?)\s*(large|medium|small)\s+(eggs|egg)',  # Handle sizes with eggs - plural first
            r'(\d+)\s*(egg|eggs)',  # Handle eggs
            r'(\d+(?:\.\d+)?)\s*(cups|tablespoons|teaspoons|ounces|pounds|grams|kilograms|milliliters|liters|tbsp|tsp|oz|lb|g|kg|ml|l)',  # Plurals
            r'(\d+(?:\.\d+)?)\s*(cup|tablespoon|teaspoon|ounce|pound|gram|kilogram|milliliter|liter)',  # Singulars
            r'(\d+(?:\.\d+)?)\s*(slice|slices|clove|cloves|bunch|bunches|can|cans|jar|jars|package|packages)',
        ]
        
        # Pattern for fractions
        self.fraction_pattern = r'(\d+)/(\d+)\s*(cup|cups|tbsp|tbs|tablespoon|tablespoons|tsp|teaspoon|teaspoons|oz|ounce|ounces|lb|pound|pounds|g|gram|grams|kg|kilogram|kilograms|ml|milliliter|milliliters|l|liter|liters)'
        
        self.preparation_patterns = [
            r'(chopped|diced|minced|sliced|grated|crushed|drained|rinsed|peeled|seeded|stemmed|trimmed|melted)',
        ]
        
        # Unit normalization mapping
        self.unit_normalization = {
            'cups': 'cup',
            'tablespoons': 'tablespoon',
            'teaspoons': 'teaspoon',
            'ounces': 'ounce',
            'pounds': 'pound',
            'grams': 'gram',
            'kilograms': 'kilogram',
            'milliliters': 'milliliter',
            'liters': 'liter',
            'slices': 'slice',
            'cloves': 'clove',
            'bunches': 'bunch',
            'cans': 'can',
            'jars': 'jar',
            'packages': 'package',
            'eggs': 'egg',
        }
    
    def normalize_ingredient(self, raw_text: str) -> Optional[Dict]:
        """Normalize raw ingredient text to structured format"""
        try:
            # Check if we have a mapping
            mapping = IngredientMapping.objects.filter(raw_text=raw_text).first()
            if mapping and mapping.normalized_ingredient:
                return {
                    'ingredient': mapping.normalized_ingredient,
                    'quantity': mapping.quantity,
                    'unit': mapping.unit,
                    'preparation_method': mapping.preparation_method
                }
            
            # Parse ingredient
            parsed = self._parse_ingredient(raw_text)
            if not parsed:
                return None
            
            # Get or create ingredient
            ingredient, created = Ingredient.objects.get_or_create(
                name=parsed['ingredient_name']
            )
            
            # Get or create unit (normalize to singular form)
            unit = None
            if parsed['unit']:
                normalized_unit_name = self._normalize_unit_name(parsed['unit'])
                unit, _ = Unit.objects.get_or_create(name=normalized_unit_name)
            
            # Create mapping for future use
            IngredientMapping.objects.create(
                raw_text=raw_text,
                normalized_ingredient=ingredient,
                quantity=parsed['quantity'],
                unit=unit,
                preparation_method=parsed['preparation_method'],
                confidence=parsed['confidence']
            )
            
            return {
                'ingredient': ingredient,
                'quantity': parsed['quantity'],
                'unit': unit,
                'preparation_method': parsed['preparation_method']
            }
            
        except Exception as e:
            logger.error(f"Failed to normalize ingredient '{raw_text}': {str(e)}")
            return None
    
    def _normalize_unit_name(self, unit_name: str) -> str:
        """Normalize unit name to singular form"""
        return self.unit_normalization.get(unit_name, unit_name)
    
    def _parse_ingredient(self, text: str) -> Optional[Dict]:
        """Parse ingredient text into components"""
        text = text.strip().lower()
        
        # Skip malformed ingredients
        if len(text) < 3 or text in ['•', '▢', 'cup', 'cups', 'tbsp', 'tsp']:
            return None
        
        # Extract quantity and unit
        quantity = None
        unit = None
        
        # First check for fractions
        fraction_match = re.search(self.fraction_pattern, text)
        if fraction_match:
            numerator = Decimal(fraction_match.group(1))
            denominator = Decimal(fraction_match.group(2))
            quantity = numerator / denominator
            unit = fraction_match.group(3)
        else:
            # Check patterns in order of specificity (most specific first)
            for i, pattern in enumerate(self.quantity_patterns):
                match = re.search(pattern, text)
                if match:
                    groups = match.groups()
                    if len(groups) == 2:
                        # Regular pattern: quantity + unit
                        quantity = Decimal(groups[0])
                        unit = groups[1]
                    elif len(groups) == 3:
                        # Check if this is a range pattern (has '-' in the match)
                        if '-' in match.group(0):
                            # Range pattern: min_qty + max_qty + unit
                            min_qty = Decimal(groups[0])
                            max_qty = Decimal(groups[1])
                            quantity = (min_qty + max_qty) / 2  # Use average
                            unit = groups[2]
                        elif groups[1] in ['large', 'medium', 'small']:
                            # Size pattern: quantity + size + eggs
                            quantity = Decimal(groups[0])
                            unit = groups[1]  # "large", "medium", "small"
                        else:
                            # Regular 3-group pattern
                            quantity = Decimal(groups[0])
                            unit = groups[1]
                    break
        
        # Extract preparation method
        preparation_method = ""
        for pattern in self.preparation_patterns:
            match = re.search(pattern, text)
            if match:
                preparation_method = match.group(1)
                break
        
        # Extract ingredient name (remove quantity, unit, and preparation method)
        ingredient_name = text
        
        # Remove quantity and unit
        if quantity and unit:
            # Handle different patterns
            if '/' in text and 'cup' in text.lower():
                # Handle fraction patterns like "1/2 cup"
                fraction_unit_pattern = rf'\d+/\d+\s*{re.escape(unit)}s?'
                ingredient_name = re.sub(fraction_unit_pattern, '', ingredient_name)
            elif '-' in text and re.search(r'\d+\s*-\s*\d+', text):
                # Handle range patterns like "1-2 cups"
                range_unit_pattern = rf'\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?\s*{re.escape(unit)}s?'
                ingredient_name = re.sub(range_unit_pattern, '', ingredient_name)
            elif unit in ['large', 'medium', 'small']:
                # Handle size patterns like "2 large eggs" - extract the ingredient name
                size_pattern = rf'\d+(?:\.\d+)?\s*{re.escape(unit)}\s+(eggs|egg)'
                match = re.search(size_pattern, ingredient_name)
                if match:
                    ingredient_name = match.group(1)  # Extract "eggs" or "egg"
            else:
                # Handle regular patterns
                # Don't add 's' if unit is already plural
                if unit.endswith('s'):
                    unit_pattern = rf'\d+(?:\.\d+)?\s*{re.escape(unit)}'
                else:
                    unit_pattern = rf'\d+(?:\.\d+)?\s*{re.escape(unit)}s?'
                ingredient_name = re.sub(unit_pattern, '', ingredient_name)
        
        # Remove preparation method
        if preparation_method:
            ingredient_name = ingredient_name.replace(preparation_method, '')
        
        # Clean up ingredient name
        ingredient_name = re.sub(r'\s+', ' ', ingredient_name).strip()
        ingredient_name = re.sub(r'^[,\s•▢]+|[,\s•▢]+$', '', ingredient_name)
        
        if not ingredient_name or len(ingredient_name) < 2:
            return None
        
        # Calculate confidence based on parsing success
        confidence = 0.5  # Base confidence
        if quantity:
            confidence += 0.2
        if unit:
            confidence += 0.2
        if preparation_method:
            confidence += 0.1
        
        return {
            'ingredient_name': ingredient_name,
            'quantity': quantity,
            'unit': unit,
            'preparation_method': preparation_method,
            'confidence': confidence
        }


class RecipeParser:
    """Parse recipes from text content"""
    
    def parse_recipes_from_text(self, text: str) -> List[Dict]:
        """Parse multiple recipes from text content"""
        recipes = []
        
        # Split text into potential recipe sections
        sections = self._split_into_sections(text)
        
        for section in sections:
            recipe = self._parse_single_recipe(section)
            if recipe:
                recipes.append(recipe)
        
        return recipes
    
    def _split_into_sections(self, text: str) -> List[str]:
        """Split text into potential recipe sections"""
        # Look for common recipe separators
        separators = [
            r'\n\s*\n\s*\n',  # Multiple blank lines
            r'\n\s*[-=*]\s*\n',  # Lines with dashes, equals, or asterisks
            r'\n\s*Recipe\s+\d+',  # "Recipe 1", "Recipe 2", etc.
            r'\n\s*INGREDIENTS\s*\n',  # Section headers
        ]
        
        # Use the most common separator
        import re
        sections = re.split(separators[0], text)
        
        # Filter out empty or very short sections
        return [s.strip() for s in sections if len(s.strip()) > 50]
    
    def _parse_single_recipe(self, text: str) -> Optional[Dict]:
        """Parse a single recipe from text"""
        try:
            # Extract recipe name
            name = self._extract_recipe_name(text)
            
            # Extract ingredients
            ingredients = self._extract_ingredients(text)
            
            # Extract instructions
            instructions = self._extract_instructions(text)
            
            # Extract metadata
            metadata = self._extract_metadata(text)
            
            if not name or not ingredients or not instructions:
                return None
            
            return {
                'name': name,
                'ingredients': ingredients,
                'instructions': instructions,
                'metadata': metadata,
                'confidence': self._calculate_confidence(name, ingredients, instructions)
            }
            
        except Exception as e:
            logger.error(f"Failed to parse recipe: {str(e)}")
            return None
    
    def _extract_recipe_name(self, text: str) -> str:
        """Extract recipe name from text"""
        lines = text.split('\n')
        
        # Look for the first non-empty line that looks like a title
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if (line and len(line) < 100 and 
                not line.lower().startswith(('ingredients', 'instructions', 'directions', 'prep', 'cook')) and
                not line.lower().startswith(('no name', 'untitled'))):  # Skip placeholder names
                return line
        
        return "Untitled Recipe"
    
    def _extract_ingredients(self, text: str) -> List[str]:
        """Extract ingredients list from text"""
        ingredients = []
        
        # Look for ingredients section
        import re
        
        # Common patterns for ingredients
        patterns = [
            r'ingredients?[:\s]*\n(.*?)(?=\n\s*(?:instructions?|directions?|method|preparation|serves|yield|nutrition|additional|$))',
            r'ingredients?[:\s]*\n(.*?)(?=\n\s*\d+\.)',  # Stop at numbered instructions
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                ingredients_text = match.group(1)
                # Split into individual ingredients
                lines = ingredients_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith(('•', '-', '*', '1.', '2.', '3.')):
                        # Clean up the line but preserve the original content
                        cleaned_line = re.sub(r'^[•\-\*\d\.\s]+', '', line)
                        if cleaned_line and len(cleaned_line) > 2:
                            ingredients.append(line)  # Keep original line with numbers
                break
        
        # If no ingredients section found, try to extract from the whole text
        if not ingredients:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                # Look for lines that look like ingredients
                if (line and 
                    len(line) < 200 and 
                    not line.lower().startswith(('instructions', 'directions', 'method', 'prep', 'cook', 'serves', 'additional')) and
                    (any(word in line.lower() for word in ['cup', 'tbsp', 'tsp', 'oz', 'lb', 'gram', 'pound', 'ounce', 'teaspoon', 'tablespoon']) or
                     re.search(r'\d+', line))):  # Contains numbers
                    # Clean up the line before adding
                    line = re.sub(r'^[•\-\*\d\.\s]+', '', line)
                    if line and len(line) > 2:
                        ingredients.append(line)
        
        return ingredients
    
    def _extract_instructions(self, text: str) -> str:
        """Extract cooking instructions from text"""
        import re
        
        # Look for instructions section
        patterns = [
            r'instructions?[:\s]*\n(.*?)(?=\n\s*(?:serves|yield|nutrition|additional|$))',
            r'directions?[:\s]*\n(.*?)(?=\n\s*(?:serves|yield|nutrition|additional|$))',
            r'method[:\s]*\n(.*?)(?=\n\s*(?:serves|yield|nutrition|additional|$))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                instructions = match.group(1).strip()
                if len(instructions) > 20:  # Ensure we have meaningful instructions
                    return instructions
        
        # If no instructions section found, try to extract numbered steps
        numbered_pattern = r'\d+\.\s*(.*?)(?=\n\s*\d+\.|\n\s*$|\n\s*(?:serves|yield|nutrition|additional|$))'
        matches = re.findall(numbered_pattern, text, re.DOTALL)
        if matches:
            instructions = '\n'.join(matches)
            if len(instructions) > 20:
                return instructions
        
        # Try to find any text that looks like instructions (contains cooking verbs)
        cooking_verbs = ['preheat', 'bake', 'cook', 'mix', 'stir', 'add', 'combine', 'heat', 'pour', 'place', 'cover', 'simmer', 'boil', 'fry', 'grill']
        lines = text.split('\n')
        instruction_lines = []
        
        for line in lines:
            line = line.strip()
            if (line and len(line) > 10 and 
                any(verb in line.lower() for verb in cooking_verbs) and
                not line.lower().startswith(('ingredients', 'serves', 'prep', 'cook', 'total'))):
                instruction_lines.append(line)
        
        if instruction_lines:
            return '\n'.join(instruction_lines)
        
        return "Instructions not found"
    
    def _extract_metadata(self, text: str) -> Dict:
        """Extract metadata like prep time, cook time, servings, etc."""
        metadata = {}
        
        import re
        
        # Extract prep time
        prep_patterns = [
            r'prep(?:aration)?\s*time[:\s]*(\d+)\s*(?:min|minutes?)',
            r'prep[:\s]*(\d+)\s*(?:min|minutes?)',
            r'preparation[:\s]*(\d+)\s*(?:min|minutes?)',
        ]
        for pattern in prep_patterns:
            prep_match = re.search(pattern, text, re.IGNORECASE)
            if prep_match:
                metadata['prep_time'] = int(prep_match.group(1))
                break
        
        # Extract cook time
        cook_patterns = [
            r'cook(?:ing)?\s*time[:\s]*(\d+)\s*(?:min|minutes?)',
            r'cook[:\s]*(\d+)\s*(?:min|minutes?)',
            r'bake[:\s]*(\d+)\s*(?:min|minutes?)',
        ]
        for pattern in cook_patterns:
            cook_match = re.search(pattern, text, re.IGNORECASE)
            if cook_match:
                metadata['cook_time'] = int(cook_match.group(1))
                break
        
        # Extract total time
        total_patterns = [
            r'total\s*time[:\s]*(\d+)\s*(?:min|minutes?)',
            r'total[:\s]*(\d+)\s*(?:min|minutes?)',
        ]
        for pattern in total_patterns:
            total_match = re.search(pattern, text, re.IGNORECASE)
            if total_match:
                metadata['total_time'] = int(total_match.group(1))
                break
        
        # Extract servings
        serves_patterns = [
            r'serves[:\s]*(\d+)',
            r'servings[:\s]*(\d+)',
            r'yield[:\s]*(\d+)',
            r'makes[:\s]*(\d+)',
        ]
        for pattern in serves_patterns:
            serves_match = re.search(pattern, text, re.IGNORECASE)
            if serves_match:
                metadata['servings'] = int(serves_match.group(1))
                break
        
        # Extract difficulty
        difficulty_match = re.search(r'difficulty[:\s]*(easy|medium|hard|difficult)', text, re.IGNORECASE)
        if difficulty_match:
            metadata['difficulty'] = difficulty_match.group(1).lower()
        
        return metadata
    
    def _calculate_confidence(self, name: str, ingredients: List[str], instructions: str) -> float:
        """Calculate confidence score for recipe parsing"""
        confidence = 0.0
        
        # Name confidence
        if name and name != "Untitled Recipe":
            confidence += 0.2
        
        # Ingredients confidence
        if ingredients:
            confidence += min(0.4, len(ingredients) * 0.1)
        
        # Instructions confidence
        if instructions and instructions != "Instructions not found":
            confidence += min(0.4, len(instructions.split()) * 0.02)
        
        return min(1.0, confidence)
