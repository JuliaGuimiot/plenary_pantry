import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from recipe_ingestion.models import (
    IngestionSource, IngestionJob, ExtractedRecipe, 
    MultiImageSource, ProcessingLog
)
from core.models import Recipe, Ingredient, Unit


class TestCoreIngestionFunctionality(TestCase):
    """Test core recipe ingestion functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
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
    
    def test_ingestion_source_creation_and_str(self):
        """Test ingestion source creation and string representation"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Test Image Recipe'
        )
        
        self.assertEqual(source.user, self.user)
        self.assertEqual(source.source_type, 'image')
        self.assertEqual(source.source_name, 'Test Image Recipe')
        self.assertIsNotNone(source.created_at)
        
        # Test string representation
        expected_str = 'Test Image Recipe (Image Upload)'
        self.assertEqual(str(source), expected_str)
    
    def test_ingestion_source_with_file(self):
        """Test ingestion source with file upload"""
        file = SimpleUploadedFile('test.jpg', b'test image content')
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Test Image',
            source_file=file
        )
        
        self.assertIn('recipe_sources/', source.source_file.name)
        self.assertIn('test', source.source_file.name)
        self.assertEqual(source.source_type, 'image')
    
    def test_ingestion_source_with_url(self):
        """Test ingestion source with URL"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='url',
            source_name='Test URL',
            source_url='https://example.com/recipe'
        )
        
        self.assertEqual(source.source_url, 'https://example.com/recipe')
        self.assertEqual(source.source_type, 'url')
    
    def test_ingestion_source_test_flag(self):
        """Test ingestion source test flag"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Recipe',
            is_test=True
        )
        
        self.assertTrue(source.is_test)
        self.assertIn('[TEST]', str(source))
    
    def test_ingestion_job_creation_and_str(self):
        """Test ingestion job creation and string representation"""
        job = IngestionJob.objects.create(source=self.source)
        
        self.assertEqual(job.source, self.source)
        self.assertEqual(job.status, 'pending')
        self.assertIsNotNone(job.started_at)
        self.assertIsNone(job.completed_at)
        self.assertEqual(job.error_message, '')
        self.assertEqual(job.recipes_found, 0)
        self.assertEqual(job.recipes_processed, 0)
        
        # Test string representation
        expected_str = f'Job {job.id} - pending'
        self.assertEqual(str(job), expected_str)
    
    def test_ingestion_job_status_transitions(self):
        """Test ingestion job status transitions"""
        job = IngestionJob.objects.create(source=self.source)
        
        # Start processing
        job.status = 'processing'
        job.started_at = datetime.now()
        job.save()
        
        self.assertEqual(job.status, 'processing')
        self.assertIsNotNone(job.started_at)
        
        # Complete processing
        job.status = 'completed'
        job.completed_at = datetime.now()
        job.recipes_found = 2
        job.recipes_processed = 2
        job.save()
        
        self.assertEqual(job.status, 'completed')
        self.assertIsNotNone(job.completed_at)
        self.assertEqual(job.recipes_found, 2)
        self.assertEqual(job.recipes_processed, 2)
    
    def test_ingestion_job_failure_handling(self):
        """Test ingestion job failure handling"""
        job = IngestionJob.objects.create(source=self.source)
        
        # Mark as failed
        job.status = 'failed'
        job.error_message = 'Test error occurred'
        job.completed_at = datetime.now()
        job.save()
        
        self.assertEqual(job.status, 'failed')
        self.assertEqual(job.error_message, 'Test error occurred')
        self.assertIsNotNone(job.completed_at)
    
    def test_extracted_recipe_creation_and_str(self):
        """Test extracted recipe creation and string representation"""
        extracted = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Test Recipe',
            raw_instructions='Test instructions',
            raw_ingredients=['1 cup flour', '2 eggs'],
            raw_metadata={'prep_time': '10 minutes'},
            confidence_score=0.85
        )
        
        self.assertEqual(extracted.job, self.job)
        self.assertEqual(extracted.raw_name, 'Test Recipe')
        self.assertEqual(extracted.raw_instructions, 'Test instructions')
        self.assertEqual(extracted.raw_ingredients, ['1 cup flour', '2 eggs'])
        self.assertEqual(extracted.raw_metadata, {'prep_time': '10 minutes'})
        self.assertEqual(extracted.confidence_score, 0.85)
        self.assertIsNotNone(extracted.created_at)
        
        # Test string representation
        expected_str = 'Extracted: Test Recipe'
        self.assertEqual(str(extracted), expected_str)
    
    def test_extracted_recipe_ingredients_handling(self):
        """Test extracted recipe ingredients handling"""
        ingredients = [
            '1 cup all-purpose flour',
            '2 large eggs',
            '1/2 cup sugar',
            '1 tsp vanilla extract'
        ]
        
        extracted = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Test Recipe',
            raw_ingredients=ingredients
        )
        
        self.assertEqual(extracted.raw_ingredients, ingredients)
        self.assertEqual(len(extracted.raw_ingredients), 4)
        self.assertIn('1 cup all-purpose flour', extracted.raw_ingredients)
    
    def test_extracted_recipe_metadata_handling(self):
        """Test extracted recipe metadata handling"""
        metadata = {
            'prep_time': '15 minutes',
            'cook_time': '25 minutes',
            'servings': '4 people',
            'difficulty': 'easy',
            'cuisine': 'italian'
        }
        
        extracted = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Test Recipe',
            raw_metadata=metadata
        )
        
        self.assertEqual(extracted.raw_metadata, metadata)
        self.assertEqual(extracted.raw_metadata['cuisine'], 'italian')
        self.assertEqual(extracted.raw_metadata['difficulty'], 'easy')
    
    def test_multi_image_source_creation_and_str(self):
        """Test multi-image source creation and string representation"""
        file = SimpleUploadedFile('page1.jpg', b'page 1 content')
        multi_image = MultiImageSource.objects.create(
            source=self.source,
            image_file=file,
            page_number=1,
            page_type='recipe'
        )
        
        self.assertEqual(multi_image.source, self.source)
        self.assertEqual(multi_image.page_number, 1)
        self.assertEqual(multi_image.page_type, 'recipe')
        self.assertIn('recipe_sources/multi/', multi_image.image_file.name)
        self.assertIn('page1', multi_image.image_file.name)
        self.assertIsNotNone(multi_image.created_at)
        
        # Test string representation - check it contains the key elements
        str_repr = str(multi_image)
        self.assertIn('Page 1', str_repr)
        self.assertIn('(recipe)', str_repr)
    
    def test_multi_image_source_page_ordering(self):
        """Test multi-image source page ordering"""
        # Create multiple pages
        file1 = SimpleUploadedFile('page1.jpg', b'page 1 content')
        file2 = SimpleUploadedFile('page2.jpg', b'page 2 content')
        file3 = SimpleUploadedFile('page3.jpg', b'page 3 content')
        
        page3 = MultiImageSource.objects.create(
            source=self.source,
            image_file=file3,
            page_number=3,
            page_type='recipe'
        )
        
        page1 = MultiImageSource.objects.create(
            source=self.source,
            image_file=file1,
            page_number=1,
            page_type='recipe'
        )
        
        page2 = MultiImageSource.objects.create(
            source=self.source,
            image_file=file2,
            page_number=2,
            page_type='recipe'
        )
        
        # Test ordering by page number
        ordered_pages = MultiImageSource.objects.filter(source=self.source).order_by('page_number')
        self.assertEqual(ordered_pages[0], page1)
        self.assertEqual(ordered_pages[1], page2)
        self.assertEqual(ordered_pages[2], page3)
    
    def test_multi_image_source_text_extraction(self):
        """Test multi-image source text extraction tracking"""
        file = SimpleUploadedFile('page1.jpg', b'page 1 content')
        multi_image = MultiImageSource.objects.create(
            source=self.source,
            image_file=file,
            page_number=1,
            page_type='recipe'
        )
        
        # Initially no extracted text
        self.assertEqual(multi_image.extracted_text, '')
        
        # Add extracted text
        extracted_text = 'Recipe ingredients and instructions from page 1'
        multi_image.extracted_text = extracted_text
        multi_image.save()
        
        self.assertEqual(multi_image.extracted_text, extracted_text)
    
    def test_multi_image_source_page_type_choices(self):
        """Test multi-image source page type choices"""
        file = SimpleUploadedFile('page1.jpg', b'page 1 content')
        
        # Test different page types
        page_types = ['recipe', 'ingredients', 'instructions', 'nutrition', 'other']
        for i, page_type in enumerate(page_types, start=1):
            file = SimpleUploadedFile(f'page{i}.jpg', f'page {i} content'.encode())
            multi_image = MultiImageSource.objects.create(
                source=self.source,
                image_file=file,
                page_number=i,
                page_type=page_type
            )
            
            self.assertEqual(multi_image.page_type, page_type)
    
    def test_processing_log_creation_and_str(self):
        """Test processing log creation and string representation"""
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
        
        # Test string representation - check it contains the key elements
        str_repr = str(log)
        self.assertIn('ocr_processing', str_repr)
        self.assertIn('OCR processing started', str_repr)
    
    def test_processing_log_levels(self):
        """Test processing log levels"""
        levels = ['debug', 'info', 'warning', 'error', 'critical']
        
        for i, level in enumerate(levels):
            log = ProcessingLog.objects.create(
                job=self.job,
                step='test_step',
                level=level,
                message=f'Test {level} message'
            )
            
            self.assertEqual(log.level, level)
    
    def test_processing_log_steps(self):
        """Test processing log steps"""
        steps = ['general', 'ocr_processing', 'text_parsing', 'ingredient_extraction', 'recipe_creation']
        
        for i, step in enumerate(steps):
            log = ProcessingLog.objects.create(
                job=self.job,
                step=step,
                level='info',
                message=f'Test {step} message'
            )
            
            self.assertEqual(log.step, step)
    
    def test_processing_log_timestamp_ordering(self):
        """Test processing log timestamp ordering"""
        # Create logs with different timestamps
        log1 = ProcessingLog.objects.create(
            job=self.job,
            step='step1',
            level='info',
            message='First message'
        )
        
        # Wait a bit
        import time
        time.sleep(0.001)
        
        log2 = ProcessingLog.objects.create(
            job=self.job,
            step='step2',
            level='info',
            message='Second message'
        )
        
        # Test ordering by timestamp
        ordered_logs = ProcessingLog.objects.filter(job=self.job).order_by('created_at')
        self.assertEqual(ordered_logs[0], log1)
        self.assertEqual(ordered_logs[1], log2)
    
    def test_ingestion_source_user_relationship(self):
        """Test ingestion source user relationship"""
        # Create multiple sources for the same user
        source1 = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Source 1'
        )
        
        source2 = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Source 2'
        )
        
        # Test user relationship
        user_sources = IngestionSource.objects.filter(user=self.user)
        self.assertEqual(user_sources.count(), 3)  # Including self.source from setUp
        self.assertIn(source1, user_sources)
        self.assertIn(source2, user_sources)
    
    def test_ingestion_job_source_relationship(self):
        """Test ingestion job source relationship"""
        # Create multiple jobs for the same source
        job1 = IngestionJob.objects.create(source=self.source)
        job2 = IngestionJob.objects.create(source=self.source)
        
        # Test source relationship
        source_jobs = IngestionJob.objects.filter(source=self.source)
        self.assertEqual(source_jobs.count(), 3)  # Including self.job from setUp
        self.assertIn(job1, source_jobs)
        self.assertIn(job2, source_jobs)
    
    def test_extracted_recipe_job_relationship(self):
        """Test extracted recipe job relationship"""
        # Create multiple extracted recipes for the same job
        extracted1 = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Recipe 1'
        )
        
        extracted2 = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Recipe 2'
        )
        
        # Test job relationship
        job_extracted = ExtractedRecipe.objects.filter(job=self.job)
        self.assertEqual(job_extracted.count(), 2)
        self.assertIn(extracted1, job_extracted)
        self.assertIn(extracted2, job_extracted)
    
    def test_multi_image_source_source_relationship(self):
        """Test multi-image source relationship"""
        # Create multiple multi-images for the same source
        file1 = SimpleUploadedFile('page1.jpg', b'page 1 content')
        file2 = SimpleUploadedFile('page2.jpg', b'page 2 content')
        
        multi1 = MultiImageSource.objects.create(
            source=self.source,
            image_file=file1,
            page_number=1,
            page_type='recipe'
        )
        
        multi2 = MultiImageSource.objects.create(
            source=self.source,
            image_file=file2,
            page_number=2,
            page_type='ingredients'
        )
        
        # Test source relationship
        source_multi_images = MultiImageSource.objects.filter(source=self.source)
        self.assertEqual(source_multi_images.count(), 2)
        self.assertIn(multi1, source_multi_images)
        self.assertIn(multi2, source_multi_images)
    
    def test_processing_log_job_relationship(self):
        """Test processing log job relationship"""
        # Create multiple logs for the same job
        log1 = ProcessingLog.objects.create(
            job=self.job,
            step='step1',
            level='info',
            message='First log'
        )
        
        log2 = ProcessingLog.objects.create(
            job=self.job,
            step='step2',
            level='warning',
            message='Second log'
        )
        
        # Test job relationship
        job_logs = ProcessingLog.objects.filter(job=self.job)
        self.assertEqual(job_logs.count(), 2)
        self.assertIn(log1, job_logs)
        self.assertIn(log2, job_logs)
    
    def test_ingestion_source_choices(self):
        """Test ingestion source type choices"""
        source_types = ['image', 'multi_image', 'url', 'text', 'api', 'email']
        
        for i, source_type in enumerate(source_types):
            source = IngestionSource.objects.create(
                user=self.user,
                source_type=source_type,
                source_name=f'Test {source_type}'
            )
            
            self.assertEqual(source.source_type, source_type)
            self.assertIn(source_type, dict(IngestionSource.SOURCE_TYPES))
    
    def test_ingestion_job_status_choices(self):
        """Test ingestion job status choices"""
        statuses = ['pending', 'processing', 'completed', 'failed', 'partial']
        
        for i, status in enumerate(statuses):
            job = IngestionJob.objects.create(
                source=self.source,
                status=status
            )
            
            self.assertEqual(job.status, status)
            self.assertIn(status, dict(IngestionJob.STATUS_CHOICES))
    
    def test_multi_image_source_page_type_choices(self):
        """Test multi-image source page type choices"""
        page_types = ['recipe', 'ingredients', 'instructions', 'nutrition', 'other']
        
        for i, page_type in enumerate(page_types, start=1):
            file = SimpleUploadedFile(f'page{i}.jpg', f'page {i} content'.encode())
            multi_image = MultiImageSource.objects.create(
                source=self.source,
                image_file=file,
                page_number=i,
                page_type=page_type
            )
            
            self.assertEqual(multi_image.page_type, page_type)
    
    def test_processing_log_level_choices(self):
        """Test processing log level choices"""
        levels = ['debug', 'info', 'warning', 'error', 'critical']
        
        for i, level in enumerate(levels):
            log = ProcessingLog.objects.create(
                job=self.job,
                step='test_step',
                level=level,
                message=f'Test {level} message'
            )
            
            self.assertEqual(log.level, level)
    
    def test_processing_log_step_choices(self):
        """Test processing log step choices"""
        steps = ['general', 'ocr_processing', 'text_parsing', 'ingredient_extraction', 'recipe_creation']
        
        for i, step in enumerate(steps):
            log = ProcessingLog.objects.create(
                job=self.job,
                step=step,
                level='info',
                message=f'Test {step} message'
            )
            
            self.assertEqual(log.step, step)
