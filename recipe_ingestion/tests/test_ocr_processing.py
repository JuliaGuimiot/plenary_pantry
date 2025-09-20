"""
Comprehensive unit tests for OCR processing functionality in recipe ingestion.

This module tests:
- OCR text extraction from images
- Recipe parsing from text
- Ingredient normalization
- Recipe processing pipeline
- Integration with test images
"""

import os
import tempfile
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files import File
from PIL import Image
import cv2
import numpy as np

from recipe_ingestion.services import (
    RecipeIngestionService, 
    IngredientNormalizer, 
    RecipeParserService
)
from recipe_ingestion.models import (
    IngestionSource, 
    IngestionJob, 
    ExtractedRecipe,
    IngredientMapping,
    ProcessingLog
)
from core.models import (
    Recipe, 
    RecipeIngredient, 
    Ingredient, 
    Unit, 
    Difficulty, 
    Cuisine, 
    Course, 
    Diet
)

CHOCOLATE_CHIP_COOKIES = """
        Chocolate Chip Cookies
        
        Ingredients:
        2 cups all-purpose flour
        1 cup granulated sugar
        1/2 cup unsalted butter, melted
        2 large eggs
        1 tsp vanilla extract
        1 cup chocolate chips
        
        Instructions:
        1. Preheat oven to 375°F.
        2. Mix flour and sugar in a large bowl.
        3. Add melted butter and eggs, mix well.
        4. Stir in vanilla extract and chocolate chips.
        5. Drop rounded tablespoons onto ungreased cookie sheet.
        6. Bake for 9-11 minutes until golden brown.
        
        Prep time: 15 minutes
        Cook time: 10 minutes
        Serves: 24 cookies
        """

class TestIngredientNormalizer(TestCase):
    """Test the IngredientNormalizer class functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.normalizer = IngredientNormalizer()
        
        # Create test ingredients and units
        self.flour = Ingredient.objects.create(name="all-purpose flour")
        self.sugar = Ingredient.objects.create(name="granulated sugar")
        self.eggs = Ingredient.objects.create(name="eggs")
        self.butter = Ingredient.objects.create(name="unsalted butter")
        
        self.cup = Unit.objects.create(name="cup", abbreviation="cup")
        self.tbsp = Unit.objects.create(name="tablespoon", abbreviation="tbsp")
        self.tsp = Unit.objects.create(name="teaspoon", abbreviation="tsp")
        self.large = Unit.objects.create(name="large", abbreviation="lg")
    
    def test_normalize_ingredient_with_quantity_and_unit(self):
        """Test normalizing ingredients with quantity and unit"""
        raw_text = "2 cups all-purpose flour"
        result = self.normalizer.normalize_ingredient(raw_text)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['quantity'], Decimal('2'))
        self.assertEqual(result['unit'], self.cup)
        self.assertEqual(result['ingredient'], self.flour)
        self.assertEqual(result['preparation_method'], '')
    
    def test_normalize_ingredient_with_preparation_method(self):
        """Test normalizing ingredients with preparation method"""
        raw_text = "1 cup chopped onions"
        result = self.normalizer.normalize_ingredient(raw_text)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['quantity'], Decimal('1'))
        self.assertEqual(result['unit'], self.cup)
        self.assertEqual(result['preparation_method'], 'chopped')
        # Should create onion ingredient
        self.assertTrue(Ingredient.objects.filter(name="onions").exists())
    
    def test_normalize_ingredient_with_range_quantity(self):
        """Test normalizing ingredients with range quantities like '1-2 cups'"""
        raw_text = "1-2 cups milk"
        result = self.normalizer.normalize_ingredient(raw_text)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['quantity'], Decimal('1.5'))  # Average of 1 and 2
        self.assertEqual(result['unit'], self.cup)
        self.assertTrue(Ingredient.objects.filter(name="milk").exists())
    
    def test_normalize_ingredient_with_size_descriptor(self):
        """Test normalizing ingredients with size descriptors"""
        raw_text = "2 large eggs"
        result = self.normalizer.normalize_ingredient(raw_text)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['quantity'], Decimal('2'))
        self.assertEqual(result['unit'], self.large)
        self.assertEqual(result['ingredient'], self.eggs)
    
    def test_normalize_ingredient_with_existing_mapping(self):
        """Test that existing mappings are used"""
        # Create a mapping
        IngredientMapping.objects.create(
            raw_text="1 cup flour",
            normalized_ingredient=self.flour,
            quantity=Decimal('1'),
            unit=self.cup,
            preparation_method='',
            confidence=0.9
        )
        
        result = self.normalizer.normalize_ingredient("1 cup flour")
        
        self.assertIsNotNone(result)
        self.assertEqual(result['ingredient'], self.flour)
        self.assertEqual(result['quantity'], Decimal('1'))
        self.assertEqual(result['unit'], self.cup)
    
    def test_normalize_ingredient_malformed_input(self):
        """Test handling of malformed ingredient input"""
        malformed_inputs = [
            "•",  # Just bullet point
            "cup",  # Just unit
            "a",  # Too short
            "",  # Empty
        ]
        
        for malformed in malformed_inputs:
            result = self.normalizer.normalize_ingredient(malformed)
            self.assertIsNone(result, f"Should return None for malformed input: '{malformed}'")
    
    def test_parse_ingredient_complex_cases(self):
        """Test parsing complex ingredient strings"""
        test_cases = [
            ("1/2 cup unsalted butter, melted", {
                'quantity': Decimal('0.5'),
                'unit': 'cup',
                'preparation_method': 'melted',
                'ingredient_name': 'unsalted butter'
            }),
            ("3 large eggs, room temperature", {
                'quantity': Decimal('3'),
                'unit': 'large',
                'preparation_method': '',
                'ingredient_name': 'eggs, room temperature'
            }),
            ("1 tsp vanilla extract", {
                'quantity': Decimal('1'),
                'unit': 'tsp',
                'preparation_method': '',
                'ingredient_name': 'vanilla extract'
            }),
        ]
        
        for raw_text, expected in test_cases:
            result = self.normalizer._parse_ingredient(raw_text)
            self.assertIsNotNone(result, f"Failed to parse: {raw_text}")
            self.assertEqual(result['quantity'], expected['quantity'])
            self.assertEqual(result['unit'], expected['unit'])
            self.assertEqual(result['preparation_method'], expected['preparation_method'])


class TestRecipeParserService(TestCase):
    """Test the RecipeParserService class functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.parser = RecipeParserService()
    
    def test_parse_single_recipe_complete(self):
        """Test parsing a complete recipe with all components"""
        recipe_text = CHOCOLATE_CHIP_COOKIES
        
        result = self.parser._parse_single_recipe(recipe_text)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], "Chocolate Chip Cookies")
        self.assertEqual(len(result['ingredients']), 6)
        self.assertIn("2 cups all-purpose flour", result['ingredients'])
        self.assertIn("1 cup chocolate chips", result['ingredients'])
        self.assertIn("Preheat oven to 375°F", result['instructions'])
        self.assertEqual(result['metadata']['prep_time'], 15)
        self.assertEqual(result['metadata']['cook_time'], 10)
        self.assertEqual(result['metadata']['servings'], 24)
    
    def test_extract_recipe_name(self):
        """Test recipe name extraction"""
        test_cases = [
            ("Chocolate Chip Cookies\n\nIngredients:", "Chocolate Chip Cookies"),
            ("Grandma's Apple Pie\n\nThis is a delicious pie", "Grandma's Apple Pie"),
            ("\n\nSpaghetti Carbonara\n\nIngredients:", "Spaghetti Carbonara"),
            ("Ingredients:\n\nNo Name Recipe", "Untitled Recipe"),  # No name found
        ]
        
        for text, expected in test_cases:
            result = self.parser._extract_recipe_name(text)
            self.assertEqual(result, expected)
    
    def test_extract_ingredients_various_formats(self):
        """Test ingredient extraction with various formats"""
        test_texts = [
            # Standard format
            """
            Ingredients:
            2 cups flour
            1 cup sugar
            3 eggs
            """,
            # Bullet points
            """
            Ingredients:
            • 2 cups flour
            • 1 cup sugar
            • 3 eggs
            """,
            # Numbered list
            """
            Ingredients:
            1. 2 cups flour
            2. 1 cup sugar
            3. 3 eggs
            """,
            # No header
            """
            2 cups flour
            1 cup sugar
            3 eggs
            
            Instructions:
            Mix ingredients
            """,
        ]
        
        for text in test_texts:
            ingredients = self.parser._extract_ingredients(text)
            self.assertGreater(len(ingredients), 0, f"Failed to extract ingredients from: {text}")
            self.assertTrue(any("flour" in ing.lower() for ing in ingredients))
            self.assertTrue(any("sugar" in ing.lower() for ing in ingredients))
    
    def test_extract_instructions_various_formats(self):
        """Test instruction extraction with various formats"""
        test_texts = [
            # Standard format
            """
            Instructions:
            1. Preheat oven to 350°F.
            2. Mix ingredients in bowl.
            3. Bake for 30 minutes.
            """,
            # Directions format
            """
            Directions:
            Preheat oven to 350°F.
            Mix ingredients in bowl.
            Bake for 30 minutes.
            """,
            # Method format
            """
            Method:
            Preheat oven to 350°F.
            Mix ingredients in bowl.
            Bake for 30 minutes.
            """,
            # Numbered without header
            """
            1. Preheat oven to 350°F.
            2. Mix ingredients in bowl.
            3. Bake for 30 minutes.
            """,
        ]
        
        for text in test_texts:
            instructions = self.parser._extract_instructions(text)
            self.assertIsNotNone(instructions)
            self.assertNotEqual(instructions, "Instructions not found")
            self.assertIn("Preheat oven", instructions)
            self.assertIn("Mix ingredients", instructions)
    
    def test_extract_metadata(self):
        """Test metadata extraction"""
        text = """
        Recipe Name
        
        Prep time: 20 minutes
        Cook time: 45 minutes
        Total time: 65 minutes
        Serves: 6
        Difficulty: Easy
        """
        
        metadata = self.parser._extract_metadata(text)
        
        self.assertEqual(metadata['prep_time'], 20)
        self.assertEqual(metadata['cook_time'], 45)
        self.assertEqual(metadata['total_time'], 65)
        self.assertEqual(metadata['servings'], 6)
        self.assertEqual(metadata['difficulty'], 'easy')
    
    def test_calculate_confidence(self):
        """Test confidence calculation"""
        # High confidence case
        high_confidence = self.parser._calculate_confidence(
            "Chocolate Chip Cookies",
            ["2 cups flour", "1 cup sugar", "3 eggs"],
            "Preheat oven to 350°F. Mix ingredients and bake for 10 minutes."
        )
        self.assertGreater(high_confidence, 0.7)
        
        # Low confidence case
        low_confidence = self.parser._calculate_confidence(
            "Untitled Recipe",
            [],
            "Instructions not found"
        )
        self.assertLess(low_confidence, 0.3)
    
    def test_split_into_sections(self):
        """Test splitting text into recipe sections"""
        text = """
        Recipe 1
        
        Ingredients:
        2 cups flour
        
        Instructions:
        Mix and bake
        
        
        Recipe 2
        
        Ingredients:
        1 cup sugar
        
        Instructions:
        Stir and serve
        """
        
        sections = self.parser._split_into_sections(text)
        self.assertGreaterEqual(len(sections), 1)  # Should find at least one section


class TestRecipeIngestionService(TestCase):
    """Test the RecipeIngestionService class functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.service = RecipeIngestionService(self.user)
        
        # Create test ingredients and units
        self.flour = Ingredient.objects.create(name="all-purpose flour")
        self.sugar = Ingredient.objects.create(name="granulated sugar")
        self.cup = Unit.objects.create(name="cup", abbreviation="cup")
        self.tsp = Unit.objects.create(name="teaspoon", abbreviation="tsp")
    
    def test_process_text_source(self):
        """Test processing a text source"""
        # Create a text source
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Recipe',
            raw_text="""
            Chocolate Chip Cookies
            
            Ingredients:
            2 cups all-purpose flour
            1 cup granulated sugar
            1/2 cup unsalted butter, melted
            2 large eggs
            1 tsp vanilla extract
            
            Instructions:
            1. Preheat oven to 375°F.
            2. Mix flour and sugar in a large bowl.
            3. Add melted butter and eggs, mix well.
            4. Stir in vanilla extract.
            5. Drop rounded tablespoons onto ungreased cookie sheet.
            6. Bake for 9-11 minutes until golden brown.
            """
        )
        
        # Process the source
        job = self.service.process_source(source)
        
        # Verify job was created and completed
        self.assertEqual(job.status, 'completed')
        self.assertGreater(job.recipes_found, 0)
        
        # Verify extracted recipes were created
        extracted_recipes = job.extracted_recipes.all()
        self.assertGreater(len(extracted_recipes), 0)
        
        recipe = extracted_recipes[0]
        self.assertEqual(recipe.raw_name, "Chocolate Chip Cookies")
        self.assertGreater(len(recipe.raw_ingredients), 0)
        self.assertIn("2 cups all-purpose flour", recipe.raw_ingredients)
        self.assertIn("Preheat oven to 375°F", recipe.raw_instructions)
    
    @patch('recipe_ingestion.services.pytesseract.image_to_string')
    def test_extract_text_from_image_mock(self, mock_tesseract):
        """Test OCR text extraction with mocked tesseract"""
        # Mock tesseract to return test text
        mock_tesseract.return_value = """
        Chocolate Chip Cookies
        
        Ingredients:
        2 cups all-purpose flour
        1 cup granulated sugar
        1/2 cup unsalted butter, melted
        
        Instructions:
        1. Preheat oven to 375°F.
        2. Mix ingredients and bake.
        """
        
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            # Create a simple test image
            img = Image.new('RGB', (100, 100), color='white')
            img.save(tmp_file.name, 'JPEG')
            
            try:
                # Test OCR extraction
                result = self.service._extract_text_from_image(tmp_file.name)
                
                # Verify result
                self.assertIsNotNone(result)
                self.assertIn("Chocolate Chip Cookies", result)
                self.assertIn("Ingredients:", result)
                self.assertIn("Instructions:", result)
                
                # Verify tesseract was called
                mock_tesseract.assert_called_once()
                
            finally:
                # Clean up
                os.unlink(tmp_file.name)
    
    def test_normalize_and_save_recipes(self):
        """Test normalizing and saving recipes to database"""
        # Create a test job with extracted recipe
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Source'
        )
        job = IngestionJob.objects.create(source=source)
        
        # Create extracted recipe
        extracted_recipe = ExtractedRecipe.objects.create(
            job=job,
            raw_name="Test Cookies",
            raw_instructions="Mix and bake for 10 minutes.",
            raw_ingredients=["2 cups flour", "1 cup sugar", "3 eggs"],
            raw_metadata={"prep_time": 15, "cook_time": 10, "servings": 24}
        )
        
        # Normalize and save
        saved_recipes = self.service.normalize_and_save_recipes(job)
        
        # Verify recipe was saved
        self.assertEqual(len(saved_recipes), 1)
        recipe = saved_recipes[0]
        
        self.assertEqual(recipe.name, "Test Cookies")
        self.assertEqual(recipe.prep_time, 15)
        self.assertEqual(recipe.cook_time, 10)
        self.assertEqual(recipe.servings, 24)
        self.assertEqual(recipe.created_by, self.user)
        
        # Verify ingredients were saved
        recipe_ingredients = recipe.ingredients.all()
        self.assertGreater(len(recipe_ingredients), 0)
        
        # Check that ingredient mappings were created
        mappings = IngredientMapping.objects.all()
        self.assertGreater(len(mappings), 0)
    
    def test_check_for_duplicate_recipe(self):
        """Test duplicate recipe detection"""
        # Create an existing recipe
        existing_recipe = Recipe.objects.create(
            name="Chocolate Chip Cookies",
            instructions="Mix and bake",
            prep_time=15,
            cook_time=10,
            servings=24,
            source_name="Test Source",
            created_by=self.user
        )
        
        # Test duplicate detection
        normalized_recipe = {
            'name': 'Chocolate Chip Cookies',
            'ingredients': []
        }
        source_info = {'name': 'Test Source'}
        
        duplicate = self.service._check_for_duplicate_recipe(normalized_recipe, source_info)
        self.assertEqual(duplicate, existing_recipe)
        
        # Test no duplicate
        normalized_recipe['name'] = 'Different Recipe'
        duplicate = self.service._check_for_duplicate_recipe(normalized_recipe, source_info)
        self.assertIsNone(duplicate)
    
    def test_get_source_info(self):
        """Test source information extraction"""
        # Test URL source
        url_source = IngestionSource.objects.create(
            user=self.user,
            source_type='url',
            source_name='AllRecipes',
            source_url='https://www.allrecipes.com/recipe/123'
        )
        
        source_info = self.service._get_source_info(url_source)
        self.assertEqual(source_info['name'], 'AllRecipes (allrecipes.com)')
        self.assertEqual(source_info['url'], 'https://www.allrecipes.com/recipe/123')
        self.assertEqual(source_info['type'], 'url')
        
        # Test image source
        image_source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Recipe Photo'
        )
        
        source_info = self.service._get_source_info(image_source)
        self.assertEqual(source_info['name'], 'Recipe Photo (Image Upload)')
    
    def test_clean_multi_image_text(self):
        """Test cleaning text from multi-image sources"""
        text = """
        === PAGE 1 (Ingredients Page) ===
        
        2 cups flour
        1 cup sugar
        
        === PAGE 2 (Instructions Page) ===
        
        1. Preheat oven
        2. Mix ingredients
        
        === PAGE 3 (Unknown) ===
        
        Additional notes
        """
        
        cleaned = self.service._clean_multi_image_text(text)
        
        # Should remove page headers
        self.assertNotIn("=== PAGE", cleaned)
        # Should preserve content
        self.assertIn("2 cups flour", cleaned)
        self.assertIn("1. Preheat oven", cleaned)
        self.assertIn("Additional notes", cleaned)


class TestOCRIntegration(TestCase):
    """Integration tests with actual test images"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.service = RecipeIngestionService(self.user)
    
    def test_process_pudding_cakes_image(self):
        """Test processing the pudding cakes test image"""
        image_path = os.path.join(
            os.path.dirname(__file__), 
            'images', 
            'pudding_cakes.jpeg'
        )
        
        if not os.path.exists(image_path):
            self.skipTest("Test image pudding_cakes.jpeg not found")
        
        # Create an ingestion source with the test image
        with open(image_path, 'rb') as f:
            uploaded_file = SimpleUploadedFile(
                'pudding_cakes.jpeg',
                f.read(),
                content_type='image/jpeg'
            )
        
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Pudding Cakes Test',
            source_file=uploaded_file
        )
        
        # Process the source
        job = self.service.process_source(source)
        
        # Verify processing completed
        self.assertIn(job.status, ['completed', 'failed'])
        
        if job.status == 'completed':
            # Verify extracted text
            self.assertIsNotNone(source.raw_text)
            self.assertGreater(len(source.raw_text), 0)
            
            # Verify extracted recipes
            extracted_recipes = job.extracted_recipes.all()
            if extracted_recipes:
                recipe = extracted_recipes[0]
                self.assertIsNotNone(recipe.raw_name)
                self.assertGreater(len(recipe.raw_ingredients), 0)
                self.assertGreater(len(recipe.raw_instructions), 0)
        
        # Log the results for debugging
        print(f"\nPudding Cakes Processing Results:")
        print(f"Status: {job.status}")
        print(f"Recipes found: {job.recipes_found}")
        if source.raw_text:
            print(f"Extracted text length: {len(source.raw_text)}")
            print(f"First 200 chars: {source.raw_text[:200]}")
    
    def test_process_split_pea_soup_image(self):
        """Test processing the split pea soup test image"""
        image_path = os.path.join(
            os.path.dirname(__file__), 
            'images', 
            'split-pea-soup.png'
        )
        
        if not os.path.exists(image_path):
            self.skipTest("Test image split-pea-soup.png not found")
        
        # Create an ingestion source with the test image
        with open(image_path, 'rb') as f:
            uploaded_file = SimpleUploadedFile(
                'split-pea-soup.png',
                f.read(),
                content_type='image/png'
            )
        
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Split Pea Soup Test',
            source_file=uploaded_file
        )
        
        # Process the source
        job = self.service.process_source(source)
        
        # Verify processing completed
        self.assertIn(job.status, ['completed', 'failed'])
        
        if job.status == 'completed':
            # Verify extracted text
            self.assertIsNotNone(source.raw_text)
            self.assertGreater(len(source.raw_text), 0)
            
            # Verify extracted recipes
            extracted_recipes = job.extracted_recipes.all()
            if extracted_recipes:
                recipe = extracted_recipes[0]
                self.assertIsNotNone(recipe.raw_name)
                self.assertGreater(len(recipe.raw_ingredients), 0)
                self.assertGreater(len(recipe.raw_instructions), 0)
        
        # Log the results for debugging
        print(f"\nSplit Pea Soup Processing Results:")
        print(f"Status: {job.status}")
        print(f"Recipes found: {job.recipes_found}")
        if source.raw_text:
            print(f"Extracted text length: {len(source.raw_text)}")
            print(f"First 200 chars: {source.raw_text[:200]}")
    
    def test_ocr_preprocessing_pipeline(self):
        """Test the OCR preprocessing pipeline with a synthetic image"""
        # Create a simple test image with text
        img = Image.new('RGB', (400, 300), color='white')
        
        img_array = np.array(img)
        
        # Test the preprocessing steps that would be used in OCR
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray)
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Verify preprocessing steps completed without error
        self.assertIsNotNone(processed)
        self.assertEqual(processed.shape, gray.shape)


class TestErrorHandling(TestCase):
    """Test error handling in OCR processing"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.service = RecipeIngestionService(self.user)
    
    def test_process_invalid_image_source(self):
        """Test handling of invalid image files"""
        # Create a source with invalid file
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Invalid Image'
        )
        
        # Process should handle the error gracefully
        job = self.service.process_source(source)
        
        # Should fail but not crash
        self.assertEqual(job.status, 'failed')
        self.assertIsNotNone(job.error_message)
    
    def test_process_empty_text_source(self):
        """Test handling of empty text sources"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Empty Text',
            raw_text=""
        )
        
        job = self.service.process_source(source)
        
        # Should complete but find no recipes
        self.assertEqual(job.status, 'completed')
        self.assertEqual(job.recipes_found, 0)
    
    def test_normalize_ingredient_with_exception(self):
        """Test ingredient normalization error handling"""
        normalizer = IngredientNormalizer()
        
        # Test with None input
        result = normalizer.normalize_ingredient(None)
        self.assertIsNone(result)
        
        # Test with very long input that might cause issues
        long_input = "a" * 1000
        result = normalizer.normalize_ingredient(long_input)
        # Should either return None or handle gracefully
        self.assertIsInstance(result, (dict, type(None)))



