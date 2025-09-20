import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from recipe_ingestion.services import RecipeIngestionService
from recipe_ingestion.models import (
    IngestionSource, IngestionJob, ExtractedRecipe, 
    MultiImageSource, ProcessingLog
)
from core.models import Recipe, Ingredient, Unit


class TestRecipeIngestionService(TestCase):
    """Test the RecipeIngestionService class"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.service = RecipeIngestionService(self.user)
        
        # Create test ingredients and units
        self.unit = Unit.objects.create(name='cup', abbreviation='cup')
        self.ingredient = Ingredient.objects.create(name='flour', description='All-purpose flour')
        
        # Create test source
        self.source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Recipe',
            raw_text='Test recipe content'
        )
        
        # Create test job
        self.job = IngestionJob.objects.create(source=self.source)
    
    def test_process_source_with_unsupported_type(self):
        """Test processing source with unsupported type raises error"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='unsupported',
            source_name='Test'
        )
        
        with self.assertRaises(ValueError) as context:
            self.service.process_source(source)
        
        self.assertIn('Unsupported source type: unsupported', str(context.exception))
        
        # Check job was marked as failed
        job = IngestionJob.objects.get(source=source)
        self.assertEqual(job.status, 'failed')
        self.assertIn('Unsupported source type', job.error_message)
    
    def test_process_source_exception_handling(self):
        """Test exception handling during source processing"""
        # Mock the _process_text_source to raise an exception
        with patch.object(self.service, '_process_text_source', side_effect=Exception('Test error')):
            job = self.service.process_source(self.source)
        
        self.assertEqual(job.status, 'failed')
        self.assertEqual(job.error_message, 'Test error')
        self.assertIsNotNone(job.error_message)
    
    def test_process_multi_image_source_no_images(self):
        """Test multi-image processing with no images raises error"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='multi_image',
            source_name='Test Multi'
        )
        
        job = IngestionJob.objects.create(source=source)
        
        with self.assertRaises(ValueError) as context:
            self.service._process_multi_image_source(job, source)
        
        self.assertIn('No images found in multi-image source', str(context.exception))
    
    @patch('recipe_ingestion.services.RecipeIngestionService._extract_text_from_image')
    def test_process_multi_image_source_with_images(self, mock_extract):
        """Test multi-image processing with images"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='multi_image',
            source_name='Test Multi'
        )
        
        # Create multi-images
        multi1 = MultiImageSource.objects.create(
            source=source,
            image_file=SimpleUploadedFile('test1.jpg', b'test1'),
            page_number=1,
            page_type='recipe'
        )
        multi2 = MultiImageSource.objects.create(
            source=source,
            image_file=SimpleUploadedFile('test2.jpg', b'test2'),
            page_number=2,
            page_type='recipe'
        )
        
        job = IngestionJob.objects.create(source=source)
        
        # Mock OCR extraction
        mock_extract.side_effect = ['Page 1 content', 'Page 2 content']
        
        # Mock recipe parser
        with patch.object(self.service.recipe_parser, 'parse_recipes_from_text') as mock_parse:
            mock_parse.return_value = [
                {
                    'name': 'Test Recipe',
                    'instructions': 'Test instructions',
                    'ingredients': ['1 cup flour'],
                    'metadata': {},
                    'confidence': 0.8
                }
            ]
            
            self.service._process_multi_image_source(job, source)
        
        # Check that text was extracted and stored
        multi1.refresh_from_db()
        multi2.refresh_from_db()
        self.assertEqual(multi1.extracted_text, 'Page 1 content')
        self.assertEqual(multi2.extracted_text, 'Page 2 content')
        
        # Check job was updated
        job.refresh_from_db()
        self.assertEqual(job.recipes_found, 1)
        self.assertEqual(job.recipes_processed, 1)
    
    @patch('recipe_ingestion.services.RecipeIngestionService._extract_text_from_image')
    def test_process_multi_image_source_with_exception(self, mock_extract):
        """Test multi-image processing handles exceptions gracefully"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='multi_image',
            source_name='Test Multi'
        )
        
        # Create multi-images
        multi1 = MultiImageSource.objects.create(
            source=source,
            image_file=SimpleUploadedFile('test1.jpg', b'test1'),
            page_number=1,
            page_type='recipe'
        )
        multi2 = MultiImageSource.objects.create(
            source=source,
            image_file=SimpleUploadedFile('test2.jpg', b'test2'),
            page_number=2,
            page_type='recipe'
        )
        
        job = IngestionJob.objects.create(source=source)
        
        # Mock OCR extraction with exception on second image
        mock_extract.side_effect = ['Page 1 content', Exception('OCR failed')]
        
        # Mock recipe parser
        with patch.object(self.service.recipe_parser, 'parse_recipes_from_text') as mock_parse:
            mock_parse.return_value = []
            
            self.service._process_multi_image_source(job, source)
        
        # Check that first image was processed
        multi1.refresh_from_db()
        self.assertEqual(multi1.extracted_text, 'Page 1 content')
        
        # Check that second image failed but didn't crash the process
        multi2.refresh_from_db()
        self.assertEqual(multi2.extracted_text, '')
        
        # Check job was updated
        job.refresh_from_db()
        self.assertEqual(job.recipes_found, 0)
        self.assertEqual(job.recipes_processed, 0)
    
    def test_clean_multi_image_text(self):
        """Test text cleaning for multi-image sources"""
        text = """=== PAGE 1 (recipe) ===
        Recipe Title
        
        === PAGE 2 (recipe) ===
        Ingredients
        
        === PAGE 3 (recipe) ===
        Instructions
        
        
        Extra whitespace
        
        
        """
        
        cleaned = self.service._clean_multi_image_text(text)
        
        # Check page headers were removed
        self.assertNotIn('=== PAGE', cleaned)
        
        # Check excessive whitespace was cleaned
        self.assertNotIn('\n\n\n', cleaned)
        
        # Check content was preserved
        self.assertIn('Recipe Title', cleaned)
        self.assertIn('Ingredients', cleaned)
        self.assertIn('Instructions', cleaned)
    
    @patch('recipe_ingestion.services.RecipeIngestionService._extract_content_from_url')
    def test_process_url_source(self, mock_extract):
        """Test URL source processing"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='url',
            source_name='Test URL',
            source_url='https://example.com/recipe'
        )
        
        job = IngestionJob.objects.create(source=source)
        
        # Mock content extraction
        mock_extract.return_value = 'Recipe content from URL'
        
        # Mock recipe parser
        with patch.object(self.service.recipe_parser, 'parse_recipes_from_text') as mock_parse:
            mock_parse.return_value = [
                {
                    'name': 'URL Recipe',
                    'instructions': 'URL instructions',
                    'ingredients': ['1 cup flour'],
                    'metadata': {'source': 'url'},
                    'confidence': 0.9
                }
            ]
            
            self.service._process_url_source(job, source)
        
        # Check source was updated
        source.refresh_from_db()
        self.assertEqual(source.raw_text, 'Recipe content from URL')
        self.assertIsNotNone(source.processed_at)
        
        # Check job was updated
        job.refresh_from_db()
        self.assertEqual(job.recipes_found, 1)
        self.assertEqual(job.recipes_processed, 1)
    
    def test_process_email_source(self):
        """Test email source processing"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='email',
            source_name='Test Email',
            raw_text='Recipe content from email'
        )
        
        job = IngestionJob.objects.create(source=source)
        
        # Mock recipe parser
        with patch.object(self.service.recipe_parser, 'parse_recipes_from_text') as mock_parse:
            mock_parse.return_value = [
                {
                    'name': 'Email Recipe',
                    'instructions': 'Email instructions',
                    'ingredients': ['1 cup flour'],
                    'metadata': {'source': 'email'},
                    'confidence': 0.85
                }
            ]
            
            self.service._process_email_source(job, source)
        
        # Check source was updated
        source.refresh_from_db()
        self.assertIsNotNone(source.processed_at)
        
        # Check job was updated
        job.refresh_from_db()
        self.assertEqual(job.recipes_found, 1)
        self.assertEqual(job.recipes_processed, 1)
    
    def test_check_for_duplicate_recipe_exact_match(self):
        """Test duplicate recipe detection with exact match"""
        # Create existing recipe
        existing_recipe = Recipe.objects.create(
            name='Test Recipe',
            description='Test description',
            instructions='Test instructions',
            prep_time=10,
            cook_time=20,
            servings=4,
            created_by=self.user
        )
        
        # Test exact match
        is_duplicate = self.service._check_for_duplicate_recipe(
            'Test Recipe', 'Test description', 'Test instructions'
        )
        
        self.assertTrue(is_duplicate)
        self.assertEqual(is_duplicate, existing_recipe)
    
    def test_check_for_duplicate_recipe_no_match(self):
        """Test duplicate recipe detection with no match"""
        # Test no match
        is_duplicate = self.service._check_for_duplicate_recipe(
            'Different Recipe', 'Different description', 'Different instructions'
        )
        
        self.assertFalse(is_duplicate)
    
    def test_check_for_duplicate_recipe_partial_match(self):
        """Test duplicate recipe detection with partial match"""
        # Create existing recipe
        existing_recipe = Recipe.objects.create(
            name='Test Recipe',
            description='Test description',
            instructions='Test instructions',
            prep_time=10,
            cook_time=20,
            servings=4,
            created_by=self.user
        )
        
        # Test partial match (should not be considered duplicate)
        is_duplicate = self.service._check_for_duplicate_recipe(
            'Test Recipe', 'Different description', 'Test instructions'
        )
        
        self.assertFalse(is_duplicate)
    
    def test_log_processing_step(self):
        """Test logging functionality"""
        job = IngestionJob.objects.create(source=self.source)
        
        # Test logging
        self.service._log(job, "Test message", "info")
        
        # Check log was created
        log = ProcessingLog.objects.get(job=job)
        self.assertEqual(log.message, "Test message")
        self.assertEqual(log.level, "info")
        self.assertEqual(log.step, "general")
    
    def test_log_processing_step_with_custom_step(self):
        """Test logging with custom step"""
        job = IngestionJob.objects.create(source=self.source)
        
        # Test logging with custom step
        self.service._log(job, "Custom step message", "warning", "custom_step")
        
        # Check log was created
        log = ProcessingLog.objects.get(job=job)
        self.assertEqual(log.message, "Custom step message")
        self.assertEqual(log.level, "warning")
        self.assertEqual(log.step, "custom_step")
    
    def test_extract_text_from_image_mock(self):
        """Test image text extraction (mocked)"""
        # Create a mock image file
        image_file = SimpleUploadedFile('test.jpg', b'test image content')
        
        # Mock pytesseract
        with patch('recipe_ingestion.services.pytesseract.image_to_string') as mock_ocr:
            mock_ocr.return_value = 'Extracted text from image'
            
            # Mock PIL Image
            with patch('recipe_ingestion.services.Image.open') as mock_pil:
                mock_image = Mock()
                mock_pil.return_value = mock_image
                
                text = self.service._extract_text_from_image('dummy_path')
                
                self.assertEqual(text, 'Extracted text from image')
                mock_ocr.assert_called_once()
    
    def test_extract_content_from_url_mock(self):
        """Test URL content extraction (mocked)"""
        url = 'https://example.com/recipe'
        
        # Mock requests
        with patch('recipe_ingestion.services.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = '<html><body>Recipe content</body></html>'
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Mock BeautifulSoup
            with patch('recipe_ingestion.services.BeautifulSoup') as mock_bs:
                mock_soup = Mock()
                mock_soup.get_text.return_value = 'Recipe content'
                mock_bs.return_value = mock_soup
                
                content = self.service._extract_content_from_url(url)
                
                self.assertEqual(content, 'Recipe content')
                mock_get.assert_called_once_with(url, timeout=30)
    
    def test_extract_content_from_url_with_selenium(self):
        """Test URL content extraction with Selenium fallback"""
        url = 'https://example.com/recipe'
        
        # Mock requests to fail
        with patch('recipe_ingestion.services.requests.get') as mock_get:
            mock_get.side_effect = Exception('Request failed')
            
            # Mock Selenium
            with patch('recipe_ingestion.services.webdriver.Chrome') as mock_driver:
                mock_driver_instance = Mock()
                mock_driver.return_value = mock_driver_instance
                mock_driver_instance.page_source = '<html><body>Selenium content</body></html>'
                mock_driver_instance.quit.return_value = None
                
                # Mock BeautifulSoup
                with patch('recipe_ingestion.services.BeautifulSoup') as mock_bs:
                    mock_soup = Mock()
                    mock_soup.get_text.return_value = 'Selenium content'
                    mock_bs.return_value = mock_soup
                    
                    content = self.service._extract_content_from_url(url)
                    
                    self.assertEqual(content, 'Selenium content')
                    mock_driver_instance.quit.assert_called_once()
    
    def test_normalize_and_save_recipes(self):
        """Test recipe normalization and saving"""
        job = IngestionJob.objects.create(source=self.source)
        
        # Create extracted recipe
        extracted = ExtractedRecipe.objects.create(
            job=job,
            raw_name='Test Recipe',
            raw_instructions='Test instructions',
            raw_ingredients=['1 cup flour'],
            raw_metadata={'prep_time': '10 minutes'},
            confidence_score=0.8
        )
        
        # Mock ingredient normalizer
        with patch.object(self.service.ingredient_normalizer, 'normalize_ingredient') as mock_normalize:
            mock_normalize.return_value = {
                'ingredient': self.ingredient,
                'quantity': Decimal('1.0'),
                'unit': self.unit,
                'preparation_method': 'sifted'
            }
            
            # Mock recipe creation
            with patch.object(self.service, '_create_recipe_from_extracted') as mock_create:
                mock_recipe = Recipe.objects.create(
                    name='Test Recipe',
                    description='Test description',
                    instructions='Test instructions',
                    prep_time=10,
                    cook_time=20,
                    servings=4,
                    created_by=self.user
                )
                mock_create.return_value = mock_recipe
                
                self.service._normalize_and_save_recipes(job)
                
                # Check that extracted recipe was processed
                extracted.refresh_from_db()
                self.assertIsNotNone(extracted.normalized_recipe)
                self.assertEqual(extracted.normalized_recipe, mock_recipe)
    
    def test_get_source_info(self):
        """Test source information extraction"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='website',
            source_name='Test Source',
            source_url='https://example.com'
        )
        
        info = self.service._get_source_info(source)
        
        self.assertEqual(info['name'], 'Test Source')
        self.assertEqual(info['url'], 'https://example.com')
        self.assertEqual(info['type'], 'website')
    
    def test_get_source_info_no_url(self):
        """Test source information extraction without URL"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Source'
        )
        
        info = self.service._get_source_info(source)
        
        self.assertEqual(info['name'], 'Test Source')
        self.assertNotIn('url', info)
        self.assertNotIn('type', info)
