"""
Ingredient Normalizer Service for ingredient parsing and normalization.

This service handles all ingredient normalization operations including parsing
ingredient text, extracting quantities and units, and creating database mappings.
"""

import re
import logging
from typing import Dict, Optional
from decimal import Decimal

from ..models import IngredientMapping
from core.models import Ingredient, Unit
from ..utils.constants import RecipeProcessingConfig

logger = logging.getLogger(__name__)


class IngredientNormalizer:
    """Service for ingredient parsing and normalization."""
    
    def __init__(self):
        """Initialize the ingredient normalizer."""
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
        """
        Normalize raw ingredient text to structured format.
        
        Args:
            raw_text: Raw ingredient text
            
        Returns:
            Normalized ingredient dictionary or None if parsing failed
        """
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
        """
        Normalize unit name to singular form.
        
        Args:
            unit_name: Unit name to normalize
            
        Returns:
            Normalized unit name
        """
        return self.unit_normalization.get(unit_name, unit_name)
    
    def _parse_ingredient(self, text: str) -> Optional[Dict]:
        """
        Parse ingredient text into components.
        
        Args:
            text: Ingredient text to parse
            
        Returns:
            Parsed ingredient dictionary or None if parsing failed
        """
        text = text.strip().lower()
        
        # Skip malformed ingredients
        if len(text) < RecipeProcessingConfig.MIN_INGREDIENT_LENGTH or text in ['•', '▢', 'cup', 'cups', 'tbsp', 'tsp']:
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
        
        if not ingredient_name or len(ingredient_name) < RecipeProcessingConfig.MIN_RECIPE_NAME_LENGTH:
            return None
        
        # Calculate confidence based on parsing success
        confidence = RecipeProcessingConfig.OCR_CONFIDENCE_THRESHOLD  # Base confidence
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
