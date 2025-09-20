import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from recipe_ingestion.models import (
    IngestionSource, IngestionJob, ExtractedRecipe, 
    MultiImageSource, ProcessingLog, RecipeTemplate,
    IngredientMapping, ApprovedEmailSender, EmailIngestionSource,
    EmailAttachment
)
from core.models import Recipe, Ingredient, Unit


class TestIngestionSource(TestCase):
    """Test the IngestionSource model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_ingestion_source_creation(self):
        """Test creating an ingestion source"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Recipe',
            raw_text='Test recipe content'
        )
        
        self.assertEqual(source.user, self.user)
        self.assertEqual(source.source_type, 'text')
        self.assertEqual(source.source_name, 'Test Recipe')
        self.assertEqual(source.raw_text, 'Test recipe content')
        self.assertIsNotNone(source.created_at)
        self.assertIsNotNone(source.updated_at)
    
    def test_ingestion_source_str_representation(self):
        """Test string representation of ingestion source"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Test Image Recipe'
        )
        
        self.assertEqual(str(source), 'Test Image Recipe (image)')
    
    def test_ingestion_source_with_file(self):
        """Test ingestion source with file upload"""
        file = SimpleUploadedFile('test.jpg', b'test image content')
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Test Image',
            source_file=file
        )
        
        self.assertEqual(source.source_file.name, f'recipe_sources/image/{file.name}')
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
    
    def test_ingestion_source_metadata(self):
        """Test ingestion source metadata handling"""
        metadata = {
            'author': 'Test Author',
            'website': 'Test Website',
            'date_published': '2023-01-01'
        }
        
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Recipe',
            metadata=metadata
        )
        
        self.assertEqual(source.metadata, metadata)
        self.assertEqual(source.metadata['author'], 'Test Author')
    
    def test_ingestion_source_status_tracking(self):
        """Test ingestion source status tracking"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Recipe'
        )
        
        # Initially not processed
        self.assertIsNone(source.processed_at)
        self.assertIsNone(source.processing_status)
        
        # Mark as processed
        source.processing_status = 'completed'
        source.processed_at = datetime.now()
        source.save()
        
        self.assertEqual(source.processing_status, 'completed')
        self.assertIsNotNone(source.processed_at)


class TestIngestionJob(TestCase):
    """Test the IngestionJob model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Recipe'
        )
    
    def test_ingestion_job_creation(self):
        """Test creating an ingestion job"""
        job = IngestionJob.objects.create(source=self.source)
        
        self.assertEqual(job.source, self.source)
        self.assertEqual(job.status, 'pending')
        self.assertIsNotNone(job.created_at)
        self.assertIsNone(job.started_at)
        self.assertIsNone(job.completed_at)
        self.assertIsNone(job.error_message)
    
    def test_ingestion_job_str_representation(self):
        """Test string representation of ingestion job"""
        job = IngestionJob.objects.create(source=self.source)
        
        expected_str = f'Job {job.id} - {self.source.source_name} (pending)'
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
    
    def test_ingestion_job_metadata(self):
        """Test ingestion job metadata handling"""
        metadata = {
            'processing_time': '30 seconds',
            'ocr_confidence': 0.85,
            'parsing_method': 'rule_based'
        }
        
        job = IngestionJob.objects.create(
            source=self.source,
            metadata=metadata
        )
        
        self.assertEqual(job.metadata, metadata)
        self.assertEqual(job.metadata['ocr_confidence'], 0.85)


class TestExtractedRecipe(TestCase):
    """Test the ExtractedRecipe model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Recipe'
        )
        
        self.job = IngestionJob.objects.create(source=self.source)
    
    def test_extracted_recipe_creation(self):
        """Test creating an extracted recipe"""
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
    
    def test_extracted_recipe_str_representation(self):
        """Test string representation of extracted recipe"""
        extracted = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Test Recipe',
            confidence_score=0.85
        )
        
        expected_str = f'Test Recipe (confidence: 0.85)'
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
    
    def test_extracted_recipe_normalization_tracking(self):
        """Test extracted recipe normalization tracking"""
        extracted = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Test Recipe'
        )
        
        # Initially not normalized
        self.assertIsNone(extracted.normalized_recipe)
        self.assertIsNone(extracted.normalized_at)
        
        # Create a normalized recipe
        normalized_recipe = Recipe.objects.create(
            name='Normalized Test Recipe',
            description='Normalized description',
            instructions='Normalized instructions',
            prep_time=15,
            cook_time=25,
            servings=4,
            created_by=self.user
        )
        
        # Link to normalized recipe
        extracted.normalized_recipe = normalized_recipe
        extracted.normalized_at = datetime.now()
        extracted.save()
        
        self.assertEqual(extracted.normalized_recipe, normalized_recipe)
        self.assertIsNotNone(extracted.normalized_at)


class TestMultiImageSource(TestCase):
    """Test the MultiImageSource model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.source = IngestionSource.objects.create(
            user=self.user,
            source_type='multi_image',
            source_name='Test Multi Image'
        )
    
    def test_multi_image_source_creation(self):
        """Test creating a multi-image source"""
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
        self.assertEqual(multi_image.image_file.name, f'recipe_sources/multi/{file.name}')
        self.assertIsNotNone(multi_image.created_at)
    
    def test_multi_image_source_str_representation(self):
        """Test string representation of multi-image source"""
        file = SimpleUploadedFile('page1.jpg', b'page 1 content')
        multi_image = MultiImageSource.objects.create(
            source=self.source,
            image_file=file,
            page_number=1,
            page_type='recipe'
        )
        
        expected_str = f'Page 1 (recipe) - {self.source.source_name}'
        self.assertEqual(str(multi_image), expected_str)
    
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
        recipe_page = MultiImageSource.objects.create(
            source=self.source,
            image_file=file,
            page_number=1,
            page_type='recipe'
        )
        
        self.assertEqual(recipe_page.page_type, 'recipe')
        self.assertEqual(recipe_page.get_page_type_display(), 'Recipe')
        
        # Test other page types
        page_types = ['ingredients', 'instructions', 'nutrition', 'other']
        for i, page_type in enumerate(page_types, start=2):
            file = SimpleUploadedFile(f'page{i}.jpg', f'page {i} content'.encode())
            multi_image = MultiImageSource.objects.create(
                source=self.source,
                image_file=file,
                page_number=i,
                page_type=page_type
            )
            
            self.assertEqual(multi_image.page_type, page_type)


class TestProcessingLog(TestCase):
    """Test the ProcessingLog model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Recipe'
        )
        
        self.job = IngestionJob.objects.create(source=self.source)
    
    def test_processing_log_creation(self):
        """Test creating a processing log"""
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
        self.assertIsNotNone(log.timestamp)
    
    def test_processing_log_str_representation(self):
        """Test string representation of processing log"""
        log = ProcessingLog.objects.create(
            job=self.job,
            step='ocr_processing',
            level='info',
            message='OCR processing started'
        )
        
        expected_str = f'[{log.timestamp.strftime("%Y-%m-%d %H:%M:%S")}] INFO - OCR processing started'
        self.assertEqual(str(log), expected_str)
    
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
            self.assertEqual(log.get_level_display(), level.title())
    
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
            self.assertEqual(log.get_step_display(), step.replace('_', ' ').title())
    
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
        ordered_logs = ProcessingLog.objects.filter(job=self.job).order_by('timestamp')
        self.assertEqual(ordered_logs[0], log1)
        self.assertEqual(ordered_logs[1], log2)


class TestRecipeTemplate(TestCase):
    """Test the RecipeTemplate model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_recipe_template_creation(self):
        """Test creating a recipe template"""
        template = RecipeTemplate.objects.create(
            user=self.user,
            name='Italian Pasta Template',
            description='Template for Italian pasta recipes',
            template_data={
                'cuisine': 'italian',
                'course': 'main',
                'difficulty': 'medium',
                'default_ingredients': ['pasta', 'olive oil', 'garlic']
            }
        )
        
        self.assertEqual(template.user, self.user)
        self.assertEqual(template.name, 'Italian Pasta Template')
        self.assertEqual(template.description, 'Template for Italian pasta recipes')
        self.assertEqual(template.template_data['cuisine'], 'italian')
        self.assertEqual(template.template_data['default_ingredients'], ['pasta', 'olive oil', 'garlic'])
        self.assertIsNotNone(template.created_at)
    
    def test_recipe_template_str_representation(self):
        """Test string representation of recipe template"""
        template = RecipeTemplate.objects.create(
            user=self.user,
            name='Italian Pasta Template',
            description='Template for Italian pasta recipes'
        )
        
        self.assertEqual(str(template), 'Italian Pasta Template')
    
    def test_recipe_template_metadata_handling(self):
        """Test recipe template metadata handling"""
        metadata = {
            'cuisine': 'italian',
            'course': 'main',
            'difficulty': 'medium',
            'prep_time': '15 minutes',
            'cook_time': '20 minutes',
            'servings': '4 people',
            'tags': ['pasta', 'italian', 'quick']
        }
        
        template = RecipeTemplate.objects.create(
            user=self.user,
            name='Test Template',
            template_data=metadata
        )
        
        self.assertEqual(template.template_data, metadata)
        self.assertEqual(template.template_data['cuisine'], 'italian')
        self.assertEqual(template.template_data['tags'], ['pasta', 'italian', 'quick'])
    
    def test_recipe_template_is_active(self):
        """Test recipe template active status"""
        template = RecipeTemplate.objects.create(
            user=self.user,
            name='Test Template',
            is_active=True
        )
        
        self.assertTrue(template.is_active)
        
        # Deactivate template
        template.is_active = False
        template.save()
        
        self.assertFalse(template.is_active)
    
    def test_recipe_template_usage_count(self):
        """Test recipe template usage count"""
        template = RecipeTemplate.objects.create(
            user=self.user,
            name='Test Template',
            usage_count=0
        )
        
        self.assertEqual(template.usage_count, 0)
        
        # Increment usage count
        template.usage_count += 1
        template.save()
        
        self.assertEqual(template.usage_count, 1)


class TestIngredientMapping(TestCase):
    """Test the IngredientMapping model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.ingredient = Ingredient.objects.create(
            name='all-purpose flour',
            description='Standard baking flour'
        )
    
    def test_ingredient_mapping_creation(self):
        """Test creating an ingredient mapping"""
        mapping = IngredientMapping.objects.create(
            user=self.user,
            raw_text='AP flour',
            normalized_ingredient=self.ingredient,
            confidence_score=0.9
        )
        
        self.assertEqual(mapping.user, self.user)
        self.assertEqual(mapping.raw_text, 'AP flour')
        self.assertEqual(mapping.normalized_ingredient, self.ingredient)
        self.assertEqual(mapping.confidence_score, 0.9)
        self.assertIsNotNone(mapping.created_at)
    
    def test_ingredient_mapping_str_representation(self):
        """Test string representation of ingredient mapping"""
        mapping = IngredientMapping.objects.create(
            user=self.user,
            raw_text='AP flour',
            normalized_ingredient=self.ingredient
        )
        
        expected_str = f'AP flour → all-purpose flour'
        self.assertEqual(str(mapping), expected_str)
    
    def test_ingredient_mapping_confidence_scoring(self):
        """Test ingredient mapping confidence scoring"""
        # High confidence mapping
        high_conf = IngredientMapping.objects.create(
            user=self.user,
            raw_text='flour',
            normalized_ingredient=self.ingredient,
            confidence_score=0.95
        )
        
        # Low confidence mapping
        low_conf = IngredientMapping.objects.create(
            user=self.user,
            raw_text='flr',
            normalized_ingredient=self.ingredient,
            confidence_score=0.6
        )
        
        self.assertGreater(high_conf.confidence_score, low_conf.confidence_score)
        self.assertTrue(high_conf.confidence_score > 0.9)
        self.assertTrue(low_conf.confidence_score < 0.7)
    
    def test_ingredient_mapping_user_specific(self):
        """Test ingredient mapping user specificity"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # Create mapping for current user
        user_mapping = IngredientMapping.objects.create(
            user=self.user,
            raw_text='AP flour',
            normalized_ingredient=self.ingredient
        )
        
        # Create mapping for other user
        other_mapping = IngredientMapping.objects.create(
            user=other_user,
            raw_text='AP flour',
            normalized_ingredient=self.ingredient
        )
        
        # Test user-specific queries
        user_mappings = IngredientMapping.objects.filter(user=self.user)
        other_mappings = IngredientMapping.objects.filter(user=other_user)
        
        self.assertIn(user_mapping, user_mappings)
        self.assertIn(other_mapping, other_mappings)
        self.assertNotIn(user_mapping, other_mappings)
        self.assertNotIn(other_mapping, user_mappings)


class TestApprovedEmailSender(TestCase):
    """Test the ApprovedEmailSender model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_approved_email_sender_creation(self):
        """Test creating an approved email sender"""
        sender = ApprovedEmailSender.objects.create(
            user=self.user,
            email_address='recipe@example.com',
            sender_name='Recipe Service',
            is_active=True
        )
        
        self.assertEqual(sender.user, self.user)
        self.assertEqual(sender.email_address, 'recipe@example.com')
        self.assertEqual(sender.sender_name, 'Recipe Service')
        self.assertTrue(sender.is_active)
        self.assertIsNotNone(sender.created_at)
    
    def test_approved_email_sender_str_representation(self):
        """Test string representation of approved email sender"""
        sender = ApprovedEmailSender.objects.create(
            user=self.user,
            email_address='recipe@example.com',
            sender_name='Recipe Service'
        )
        
        expected_str = f'Recipe Service (recipe@example.com)'
        self.assertEqual(str(sender), expected_str)
    
    def test_approved_email_sender_validation(self):
        """Test approved email sender validation"""
        # Valid email
        valid_sender = ApprovedEmailSender.objects.create(
            user=self.user,
            email_address='valid@example.com',
            sender_name='Valid Sender'
        )
        
        self.assertEqual(valid_sender.email_address, 'valid@example.com')
        
        # Test with invalid email format (Django will handle this)
        # This is more of a form validation test, but we can test the model accepts it
        invalid_sender = ApprovedEmailSender.objects.create(
            user=self.user,
            email_address='invalid-email',
            sender_name='Invalid Sender'
        )
        
        self.assertEqual(invalid_sender.email_address, 'invalid-email')
    
    def test_approved_email_sender_active_status(self):
        """Test approved email sender active status"""
        sender = ApprovedEmailSender.objects.create(
            user=self.user,
            email_address='recipe@example.com',
            sender_name='Recipe Service',
            is_active=True
        )
        
        self.assertTrue(sender.is_active)
        
        # Deactivate sender
        sender.is_active = False
        sender.save()
        
        self.assertFalse(sender.is_active)
    
    def test_approved_email_sender_user_specific(self):
        """Test approved email sender user specificity"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # Create sender for current user
        user_sender = ApprovedEmailSender.objects.create(
            user=self.user,
            email_address='user@example.com',
            sender_name='User Sender'
        )
        
        # Create sender for other user
        other_sender = ApprovedEmailSender.objects.create(
            user=other_user,
            email_address='other@example.com',
            sender_name='Other Sender'
        )
        
        # Test user-specific queries
        user_senders = ApprovedEmailSender.objects.filter(user=self.user)
        other_senders = ApprovedEmailSender.objects.filter(user=other_user)
        
        self.assertIn(user_sender, user_senders)
        self.assertIn(other_sender, other_senders)
        self.assertNotIn(user_sender, other_senders)
        self.assertNotIn(other_sender, user_senders)


class TestEmailIngestionSource(TestCase):
    """Test the EmailIngestionSource model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_email_ingestion_source_creation(self):
        """Test creating an email ingestion source"""
        source = EmailIngestionSource.objects.create(
            user=self.user,
            email_subject='New Recipe from Mom',
            sender_email='mom@example.com',
            sender_name='Mom',
            email_body='Here is my famous chocolate chip cookie recipe...',
            received_at=datetime.now()
        )
        
        self.assertEqual(source.user, self.user)
        self.assertEqual(source.email_subject, 'New Recipe from Mom')
        self.assertEqual(source.sender_email, 'mom@example.com')
        self.assertEqual(source.sender_name, 'Mom')
        self.assertIn('chocolate chip cookie recipe', source.email_body)
        self.assertIsNotNone(source.received_at)
        self.assertIsNotNone(source.created_at)
    
    def test_email_ingestion_source_str_representation(self):
        """Test string representation of email ingestion source"""
        source = EmailIngestionSource.objects.create(
            user=self.user,
            email_subject='New Recipe from Mom',
            sender_email='mom@example.com',
            sender_name='Mom'
        )
        
        expected_str = f'New Recipe from Mom (from: mom@example.com)'
        self.assertEqual(str(source), expected_str)
    
    def test_email_ingestion_source_processing_status(self):
        """Test email ingestion source processing status"""
        source = EmailIngestionSource.objects.create(
            user=self.user,
            email_subject='Test Recipe',
            sender_email='test@example.com'
        )
        
        # Initially not processed
        self.assertIsNone(source.processed_at)
        self.assertIsNone(source.processing_status)
        
        # Mark as processed
        source.processing_status = 'completed'
        source.processed_at = datetime.now()
        source.save()
        
        self.assertEqual(source.processing_status, 'completed')
        self.assertIsNotNone(source.processed_at)
    
    def test_email_ingestion_source_metadata(self):
        """Test email ingestion source metadata handling"""
        metadata = {
            'email_id': 'msg_123456',
            'thread_id': 'thread_789',
            'labels': ['recipe', 'family'],
            'priority': 'normal'
        }
        
        source = EmailIngestionSource.objects.create(
            user=self.user,
            email_subject='Test Recipe',
            sender_email='test@example.com',
            metadata=metadata
        )
        
        self.assertEqual(source.metadata, metadata)
        self.assertEqual(source.metadata['email_id'], 'msg_123456')
        self.assertEqual(source.metadata['labels'], ['recipe', 'family'])
    
    def test_email_ingestion_source_attachments(self):
        """Test email ingestion source attachments"""
        source = EmailIngestionSource.objects.create(
            user=self.user,
            email_subject='Test Recipe with Attachments',
            sender_email='test@example.com'
        )
        
        # Initially no attachments
        self.assertEqual(source.attachments.count(), 0)
        
        # Add attachment
        attachment = EmailAttachment.objects.create(
            email_source=source,
            filename='recipe.jpg',
            content_type='image/jpeg',
            file_size=1024
        )
        
        self.assertEqual(source.attachments.count(), 1)
        self.assertEqual(source.attachments.first(), attachment)


class TestEmailAttachment(TestCase):
    """Test the EmailAttachment model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.email_source = EmailIngestionSource.objects.create(
            user=self.user,
            email_subject='Test Recipe',
            sender_email='test@example.com'
        )
    
    def test_email_attachment_creation(self):
        """Test creating an email attachment"""
        file = SimpleUploadedFile('recipe.jpg', b'recipe image content')
        attachment = EmailAttachment.objects.create(
            email_source=self.email_source,
            filename='recipe.jpg',
            content_type='image/jpeg',
            file_size=1024,
            attachment_file=file
        )
        
        self.assertEqual(attachment.email_source, self.email_source)
        self.assertEqual(attachment.filename, 'recipe.jpg')
        self.assertEqual(attachment.content_type, 'image/jpeg')
        self.assertEqual(attachment.file_size, 1024)
        self.assertEqual(attachment.attachment_file.name, f'recipe_sources/email/{file.name}')
        self.assertIsNotNone(attachment.created_at)
    
    def test_email_attachment_str_representation(self):
        """Test string representation of email attachment"""
        attachment = EmailAttachment.objects.create(
            email_source=self.email_source,
            filename='recipe.jpg',
            content_type='image/jpeg',
            file_size=1024
        )
        
        expected_str = f'recipe.jpg (1.0 KB)'
        self.assertEqual(str(attachment), expected_str)
    
    def test_email_attachment_file_size_formatting(self):
        """Test email attachment file size formatting"""
        # Test different file sizes
        sizes = [
            (1024, '1.0 KB'),
            (2048, '2.0 KB'),
            (1048576, '1.0 MB'),
            (1572864, '1.5 MB')
        ]
        
        for size_bytes, expected_format in sizes:
            attachment = EmailAttachment.objects.create(
                email_source=self.email_source,
                filename=f'test_{size_bytes}.jpg',
                content_type='image/jpeg',
                file_size=size_bytes
            )
            
            self.assertEqual(str(attachment), f'test_{size_bytes}.jpg ({expected_format})')
    
    def test_email_attachment_processing_status(self):
        """Test email attachment processing status"""
        attachment = EmailAttachment.objects.create(
            email_source=self.email_source,
            filename='recipe.jpg',
            content_type='image/jpeg',
            file_size=1024
        )
        
        # Initially not processed
        self.assertIsNone(attachment.processed_at)
        self.assertIsNone(attachment.processing_status)
        
        # Mark as processed
        attachment.processing_status = 'completed'
        attachment.processed_at = datetime.now()
        attachment.save()
        
        self.assertEqual(attachment.processing_status, 'completed')
        self.assertIsNotNone(attachment.processed_at)
    
    def test_email_attachment_metadata(self):
        """Test email attachment metadata handling"""
        metadata = {
            'content_disposition': 'attachment',
            'content_id': 'cid_123456',
            'checksum': 'abc123def456',
            'ocr_confidence': 0.85
        }
        
        attachment = EmailAttachment.objects.create(
            email_source=self.email_source,
            filename='recipe.jpg',
            content_type='image/jpeg',
            file_size=1024,
            metadata=metadata
        )
        
        self.assertEqual(attachment.metadata, metadata)
        self.assertEqual(attachment.metadata['content_disposition'], 'attachment')
        self.assertEqual(attachment.metadata['ocr_confidence'], 0.85)
