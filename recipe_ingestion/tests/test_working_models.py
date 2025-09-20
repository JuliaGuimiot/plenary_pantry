from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from decimal import Decimal

from recipe_ingestion.models import (
    IngestionSource, IngestionJob, ExtractedRecipe, 
    IngredientMapping, ProcessingLog, MultiImageSource
)

User = get_user_model()


class TestWorkingModels(TestCase):
    """Test the models that actually exist and work in recipe_ingestion"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Test Source',
            source_file=SimpleUploadedFile(
                'test.jpg',
                b'fake image content',
                content_type='image/jpeg'
            )
        )
        
        self.job = IngestionJob.objects.create(
            source=self.source,
            status='pending'
        )
    
    def test_ingestion_source_creation(self):
        """Test IngestionSource creation and basic fields"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Text Source'
        )
        
        self.assertEqual(source.user, self.user)
        self.assertEqual(source.source_type, 'text')
        self.assertEqual(source.source_name, 'Test Text Source')
        self.assertIsNotNone(source.created_at)
        self.assertFalse(source.is_test)
        self.assertIsNone(source.processed_at)
    
    def test_ingestion_source_with_file(self):
        """Test IngestionSource with file upload"""
        file = SimpleUploadedFile(
            'test_file.jpg',
            b'fake file content',
            content_type='image/jpeg'
        )
        
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Test File Source',
            source_file=file
        )
        
        self.assertIn('recipe_sources/', source.source_file.name)
        self.assertIn('test_file', source.source_file.name)
        self.assertEqual(source.source_type, 'image')
    
    def test_ingestion_source_str_representation(self):
        """Test IngestionSource string representation"""
        expected_str = f'{self.source.source_name} ({self.source.source_type})'
        self.assertEqual(str(self.source), expected_str)
    
    def test_ingestion_source_choices(self):
        """Test IngestionSource source_type choices"""
        choices = [choice[0] for choice in IngestionSource._meta.get_field('source_type').choices]
        expected_choices = ['image', 'text', 'website', 'email', 'multi']
        self.assertEqual(choices, expected_choices)
    
    def test_ingestion_job_creation(self):
        """Test IngestionJob creation and basic fields"""
        job = IngestionJob.objects.create(
            source=self.source,
            status='pending'
        )
        
        self.assertEqual(job.source, self.source)
        self.assertEqual(job.status, 'pending')
        self.assertIsNotNone(job.started_at)
        self.assertIsNone(job.completed_at)
        self.assertEqual(job.error_message, '')
        self.assertEqual(job.recipes_found, 0)
        self.assertEqual(job.recipes_processed, 0)
    
    def test_ingestion_job_status_transitions(self):
        """Test IngestionJob status field transitions"""
        self.job.status = 'processing'
        self.job.save()
        self.assertEqual(self.job.status, 'processing')
        
        self.job.status = 'completed'
        self.job.completed_at = timezone.now()
        self.job.save()
        self.assertEqual(self.job.status, 'completed')
        self.assertIsNotNone(self.job.completed_at)
    
    def test_ingestion_job_str_representation(self):
        """Test IngestionJob string representation"""
        expected_str = f'Job {self.job.id} - {self.job.status}'
        self.assertEqual(str(self.job), expected_str)
    
    def test_ingestion_job_choices(self):
        """Test IngestionJob status choices"""
        choices = [choice[0] for choice in IngestionJob._meta.get_field('status').choices]
        expected_choices = ['pending', 'processing', 'completed', 'failed']
        self.assertEqual(choices, expected_choices)
    
    def test_extracted_recipe_creation(self):
        """Test ExtractedRecipe creation and basic fields"""
        recipe = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Test Recipe',
            raw_ingredients='Ingredient 1, Ingredient 2',
            raw_instructions='Step 1, Step 2',
            confidence_score=0.85
        )
        
        self.assertEqual(recipe.job, self.job)
        self.assertEqual(recipe.raw_name, 'Test Recipe')
        self.assertEqual(recipe.raw_ingredients, 'Ingredient 1, Ingredient 2')
        self.assertEqual(recipe.raw_instructions, 'Step 1, Step 2')
        self.assertEqual(recipe.confidence_score, Decimal('0.85'))
        self.assertIsNotNone(recipe.created_at)
        self.assertIsNone(recipe.normalized_at)
    
    def test_extracted_recipe_str_representation(self):
        """Test ExtractedRecipe string representation"""
        recipe = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Test Recipe',
            raw_ingredients='Test ingredients',
            raw_instructions='Test instructions',
            confidence_score=0.85
        )
        
        expected_str = f'Extracted: {recipe.raw_name}'
        self.assertEqual(str(recipe), expected_str)
    
    def test_extracted_recipe_confidence_score_range(self):
        """Test ExtractedRecipe confidence_score field constraints"""
        # Test valid range
        recipe = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Test Recipe',
            raw_ingredients='Test ingredients',
            raw_instructions='Test instructions',
            confidence_score=0.5
        )
        self.assertEqual(recipe.confidence_score, Decimal('0.5'))
        
        # Test boundary values
        recipe.confidence_score = 0.0
        recipe.save()
        self.assertEqual(recipe.confidence_score, Decimal('0.0'))
        
        recipe.confidence_score = 1.0
        recipe.save()
        self.assertEqual(recipe.confidence_score, Decimal('1.0'))
    
    def test_multi_image_source_creation(self):
        """Test MultiImageSource creation and basic fields"""
        file = SimpleUploadedFile(
            'page1.jpg',
            b'fake page content',
            content_type='image/jpeg'
        )
        
        multi_image = MultiImageSource.objects.create(
            source=self.source,
            page_number=1,
            page_type='recipe',
            image_file=file
        )
        
        self.assertEqual(multi_image.source, self.source)
        self.assertEqual(multi_image.page_number, 1)
        self.assertEqual(multi_image.page_type, 'recipe')
        self.assertIn('recipe_sources/multi/', multi_image.image_file.name)
        self.assertIn('page1', multi_image.image_file.name)
        self.assertIsNotNone(multi_image.created_at)
    
    def test_multi_image_source_str_representation(self):
        """Test MultiImageSource string representation"""
        file = SimpleUploadedFile(
            'page1.jpg',
            b'fake page content',
            content_type='image/jpeg'
        )
        
        multi_image = MultiImageSource.objects.create(
            source=self.source,
            page_number=1,
            page_type='recipe',
            image_file=file
        )
        
        str_repr = str(multi_image)
        self.assertIn('Page 1', str_repr)
        self.assertIn('(recipe)', str_repr)
    
    def test_multi_image_source_choices(self):
        """Test MultiImageSource page_type choices"""
        choices = [choice[0] for choice in MultiImageSource._meta.get_field('page_type').choices]
        expected_choices = ['recipe', 'ingredients', 'instructions', 'other']
        self.assertEqual(choices, expected_choices)
    
    def test_processing_log_creation(self):
        """Test ProcessingLog creation and basic fields"""
        log = ProcessingLog.objects.create(
            job=self.job,
            step='ocr_processing',
            level='info',
            message='OCR processing started'
        )
        
        self.assertEqual(log.job, self.job)
        self.assertEqual(log.step, 'ocr_processing')
        self.assertEqual(log.level, 'info')
        self.assertEqual(log.message, 'OCR processing started')
        self.assertIsNotNone(log.created_at)
    
    def test_processing_log_str_representation(self):
        """Test ProcessingLog string representation"""
        log = ProcessingLog.objects.create(
            job=self.job,
            step='ocr_processing',
            level='info',
            message='OCR processing started'
        )
        
        str_repr = str(log)
        self.assertIn('ocr_processing', str_repr)
        self.assertIn('OCR processing started', str_repr)
    
    def test_processing_log_levels(self):
        """Test ProcessingLog level choices"""
        choices = [choice[0] for choice in ProcessingLog._meta.get_field('level').choices]
        expected_choices = ['debug', 'info', 'warning', 'error', 'critical']
        self.assertEqual(choices, expected_choices)
    
    def test_processing_log_steps(self):
        """Test ProcessingLog step choices"""
        choices = [choice[0] for choice in ProcessingLog._meta.get_field('step').choices]
        expected_steps = ['general', 'ocr_processing', 'text_extraction', 'recipe_parsing', 'normalization']
        self.assertEqual(choices, expected_steps)
    
    def test_ingredient_mapping_creation(self):
        """Test IngredientMapping creation and basic fields"""
        mapping = IngredientMapping.objects.create(
            raw_ingredient='tomato',
            normalized_ingredient='tomato',
            confidence_score=0.9
        )
        
        self.assertEqual(mapping.raw_ingredient, 'tomato')
        self.assertEqual(mapping.normalized_ingredient, 'tomato')
        self.assertEqual(mapping.confidence_score, Decimal('0.9'))
        self.assertIsNotNone(mapping.created_at)
        self.assertIsNone(mapping.updated_at)
    
    def test_ingredient_mapping_str_representation(self):
        """Test IngredientMapping string representation"""
        mapping = IngredientMapping.objects.create(
            raw_ingredient='tomato',
            normalized_ingredient='tomato',
            confidence_score=0.9
        )
        
        expected_str = f'{mapping.raw_ingredient} → {mapping.normalized_ingredient}'
        self.assertEqual(str(mapping), expected_str)
    
    def test_ingredient_mapping_confidence_score_range(self):
        """Test IngredientMapping confidence_score field constraints"""
        # Test valid range
        mapping = IngredientMapping.objects.create(
            raw_ingredient='test',
            normalized_ingredient='test',
            confidence_score=0.75
        )
        self.assertEqual(mapping.confidence_score, Decimal('0.75'))
        
        # Test boundary values
        mapping.confidence_score = 0.0
        mapping.save()
        self.assertEqual(mapping.confidence_score, Decimal('0.0'))
        
        mapping.confidence_score = 1.0
        mapping.save()
        self.assertEqual(mapping.confidence_score, Decimal('1.0'))
    
    def test_model_relationships(self):
        """Test relationships between models"""
        # Test IngestionJob -> IngestionSource relationship
        self.assertEqual(self.job.source, self.source)
        self.assertEqual(self.source.ingestionjob_set.first(), self.job)
        
        # Test ExtractedRecipe -> IngestionJob relationship
        recipe = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Test Recipe',
            raw_ingredients='Test ingredients',
            raw_instructions='Test instructions',
            confidence_score=0.85
        )
        self.assertEqual(recipe.job, self.job)
        self.assertIn(recipe, self.job.extractedrecipe_set.all())
        
        # Test ProcessingLog -> IngestionJob relationship
        log = ProcessingLog.objects.create(
            job=self.job,
            step='general',
            level='info',
            message='Test log message'
        )
        self.assertEqual(log.job, self.job)
        self.assertIn(log, self.job.processinglog_set.all())
        
        # Test MultiImageSource -> IngestionSource relationship
        file = SimpleUploadedFile(
            'page1.jpg',
            b'fake page content',
            content_type='image/jpeg'
        )
        multi_image = MultiImageSource.objects.create(
            source=self.source,
            page_number=1,
            page_type='recipe',
            image_file=file
        )
        self.assertEqual(multi_image.source, self.source)
        self.assertIn(multi_image, self.source.multiimagesource_set.all())
    
    def test_model_validation(self):
        """Test model field validation"""
        # Test required fields
        with self.assertRaises(Exception):
            IngestionSource.objects.create()  # Missing required fields
        
        with self.assertRaises(Exception):
            IngestionJob.objects.create()  # Missing required fields
        
        with self.assertRaises(Exception):
            ExtractedRecipe.objects.create()  # Missing required fields
        
        # Test field constraints
        with self.assertRaises(Exception):
            ExtractedRecipe.objects.create(
                job=self.job,
                raw_name='Test',
                raw_ingredients='Test',
                raw_instructions='Test',
                confidence_score=1.5  # Should be <= 1.0
            )
        
        with self.assertRaises(Exception):
            IngredientMapping.objects.create(
                raw_ingredient='test',
                normalized_ingredient='test',
                confidence_score=1.5  # Should be <= 1.0
            )
