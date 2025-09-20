"""
Recipe Normalizer Service for recipe normalization and database operations.

This service handles all recipe normalization operations including ingredient
normalization, recipe creation, duplicate detection, and database management.
"""

import logging
from typing import List, Dict, Optional
from decimal import Decimal
from urllib.parse import urlparse

from django.db import transaction
from django.contrib.auth.models import User

from ..models import (
    IngestionJob, ExtractedRecipe, IngredientMapping, ProcessingLog
)
from core.models import (
    Recipe, RecipeIngredient, Ingredient, Unit, 
    Difficulty, Cuisine, Course, Diet
)
from .ingredient_normalizer import IngredientNormalizer

logger = logging.getLogger(__name__)


class RecipeNormalizerService:
    """Service for recipe normalization and database operations."""
    
    def __init__(self, user: User):
        """
        Initialize the recipe normalizer service.
        
        Args:
            user: User who owns the recipes
        """
        self.user = user
        self.ingredient_normalizer = IngredientNormalizer()
    
    def normalize_and_save_recipes(self, job: IngestionJob) -> List[Recipe]:
        """
        Normalize and save recipes from an ingestion job.
        
        Args:
            job: Ingestion job containing extracted recipes
            
        Returns:
            List of saved Recipe objects
        """
        saved_recipes = []
        
        for extracted_recipe in job.extracted_recipes.all():
            try:
                # Normalize the recipe
                normalized_recipe = self._normalize_recipe(extracted_recipe)
                
                # Get source information
                source_info = self._get_source_info(job.source)
                
                # Check for duplicates
                existing_recipe = self._check_for_duplicate_recipe(normalized_recipe, source_info)
                
                if existing_recipe:
                    # Update existing recipe with better data
                    updated_recipe = self._update_recipe_with_better_data(existing_recipe, normalized_recipe)
                    saved_recipes.append(updated_recipe)
                    self._log(job, f"Updated existing recipe: {updated_recipe.name}", "info")
                else:
                    # Create new recipe
                    new_recipe = self._create_recipe_from_normalized(normalized_recipe, source_info)
                    saved_recipes.append(new_recipe)
                    self._log(job, f"Created new recipe: {new_recipe.name}", "info")
                
            except Exception as e:
                logger.error(f"Failed to normalize recipe: {str(e)}", exc_info=True)
                self._log(job, f"Failed to normalize recipe: {str(e)}", "error")
        
        return saved_recipes
    
    def _normalize_recipe(self, extracted_recipe: ExtractedRecipe) -> Dict:
        """
        Normalize extracted recipe data.
        
        Args:
            extracted_recipe: Extracted recipe to normalize
            
        Returns:
            Normalized recipe dictionary
        """
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
        """Get or create difficulty level."""
        if not name:
            return None
        difficulty, _ = Difficulty.objects.get_or_create(name=name.lower())
        return difficulty
    
    def _get_or_create_cuisine(self, name: str) -> Optional[Cuisine]:
        """Get or create cuisine type."""
        if not name:
            return None
        cuisine, _ = Cuisine.objects.get_or_create(name=name.lower())
        return cuisine
    
    def _get_or_create_course(self, name: str) -> Optional[Course]:
        """Get or create course type."""
        if not name:
            return None
        course, _ = Course.objects.get_or_create(name=name.lower())
        return course
    
    def _get_or_create_diet(self, name: str) -> Optional[Diet]:
        """Get or create diet type."""
        if not name:
            return None
        diet, _ = Diet.objects.get_or_create(name=name.lower())
        return diet
    
    def _get_source_info(self, source) -> Dict[str, str]:
        """
        Extract source information from ingestion source.
        
        Args:
            source: Ingestion source object
            
        Returns:
            Source information dictionary
        """
        source_info = {
            'name': source.source_name,
            'url': source.source_url or '',
            'type': source.source_type
        }
        
        # Enhance source name based on type
        if source.source_type == 'url' and source.source_url:
            # Extract domain name from URL
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
        """
        Check if a recipe with the same name, source, and user already exists.
        
        Args:
            normalized_recipe: Normalized recipe data
            source_info: Source information
            
        Returns:
            Existing recipe if found, None otherwise
        """
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
        """
        Update existing recipe with better data.
        
        Args:
            existing_recipe: Existing recipe to update
            normalized_recipe: New normalized recipe data
            
        Returns:
            Updated recipe
        """
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
    
    def _create_recipe_from_normalized(self, normalized_recipe: Dict, source_info: Dict) -> Recipe:
        """
        Create a new recipe from normalized data.
        
        Args:
            normalized_recipe: Normalized recipe data
            source_info: Source information
            
        Returns:
            Created recipe
        """
        with transaction.atomic():
            # Create the recipe
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
                source_url=source_info.get('url', ''),
                created_by=self.user
            )
            
            # Add ingredients
            for ingredient_data in normalized_recipe['ingredients']:
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient_data['ingredient'],
                    quantity=ingredient_data['quantity'],
                    unit=ingredient_data.get('unit'),
                    preparation_method=ingredient_data.get('preparation_method', '')
                )
            
            return recipe
    
    def _log(self, job: IngestionJob, message: str, level: str = 'info'):
        """
        Log processing steps.
        
        Args:
            job: Ingestion job
            message: Log message
            level: Log level
        """
        ProcessingLog.objects.create(
            job=job,
            step='normalization',
            message=message,
            level=level
        )
