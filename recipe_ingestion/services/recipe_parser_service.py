"""
Recipe Parser Service for parsing recipes from text.

This service handles all recipe parsing operations including text analysis,
ingredient extraction, instruction parsing, and metadata extraction.
"""

import re
import logging
from typing import List, Dict, Optional

from ..utils.constants import RecipeProcessingConfig

logger = logging.getLogger(__name__)


class RecipeParserService:
    """Service for parsing recipes from text content."""
    
    def __init__(self):
        """Initialize the recipe parser service."""
        self.min_ingredient_length = RecipeProcessingConfig.MIN_INGREDIENT_LENGTH
        self.min_instruction_length = RecipeProcessingConfig.MIN_INSTRUCTION_LENGTH
        self.min_recipe_name_length = RecipeProcessingConfig.MIN_RECIPE_NAME_LENGTH
    
    def parse_recipes_from_text(self, text: str) -> List[Dict]:
        """
        Parse recipes from text content.
        
        Args:
            text: Text content to parse recipes from
            
        Returns:
            List of parsed recipe dictionaries
        """
        if not text or not text.strip():
            return []
        
        # Split text into potential recipe sections
        sections = self._split_into_sections(text)
        
        recipes = []
        for section in sections:
            recipe = self._parse_single_recipe(section)
            if recipe:
                recipes.append(recipe)
        
        return recipes
    
    def _split_into_sections(self, text: str) -> List[str]:
        """
        Split text into potential recipe sections.
        
        Args:
            text: Text to split
            
        Returns:
            List of text sections
        """
        # Look for common recipe separators
        separators = [
            r'\n\s*\n\s*\n',  # Multiple blank lines
            r'\n\s*[-=*]\s*\n',  # Lines with dashes, equals, or asterisks
            r'\n\s*Recipe\s+\d+',  # "Recipe 1", "Recipe 2", etc.
            r'\n\s*INGREDIENTS\s*\n',  # Section headers
        ]
        
        # Use the most common separator
        sections = re.split(separators[0], text)
        
        # Filter out empty or very short sections
        return [s.strip() for s in sections if len(s.strip()) > 50]
    
    def _parse_single_recipe(self, text: str) -> Optional[Dict]:
        """
        Parse a single recipe from text.
        
        Args:
            text: Text section to parse
            
        Returns:
            Parsed recipe dictionary or None if parsing failed
        """
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
        """
        Extract recipe name from text.
        
        Args:
            text: Text to extract name from
            
        Returns:
            Recipe name
        """
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
        """
        Extract ingredients list from text.
        
        Args:
            text: Text to extract ingredients from
            
        Returns:
            List of ingredient strings
        """
        ingredients = []
        
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
        """
        Extract cooking instructions from text.
        
        Args:
            text: Text to extract instructions from
            
        Returns:
            Instructions text
        """
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
                if len(instructions) > self.min_instruction_length:  # Ensure we have meaningful instructions
                    return instructions
        
        # If no instructions section found, try to extract numbered steps
        numbered_pattern = r'\d+\.\s*(.*?)(?=\n\s*\d+\.|\n\s*$|\n\s*(?:serves|yield|nutrition|additional|$))'
        matches = re.findall(numbered_pattern, text, re.DOTALL)
        if matches:
            instructions = '\n'.join(matches)
            if len(instructions) > self.min_instruction_length:
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
        """
        Extract metadata like prep time, cook time, servings, etc.
        
        Args:
            text: Text to extract metadata from
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
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
        """
        Calculate confidence score for recipe parsing.
        
        Args:
            name: Recipe name
            ingredients: List of ingredients
            instructions: Instructions text
            
        Returns:
            Confidence score between 0 and 1
        """
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
