from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from recipe_ingestion.models import (
    IngestionSource, IngestionJob, ExtractedRecipe, 
    IngredientMapping, ProcessingLog, MultiImageSource,
    RecipeTemplate, ApprovedEmailSender, EmailIngestionSource, EmailAttachment
)

User = get_user_model()


class TestSimpleCoverage(TestCase):
    """Simple tests to improve coverage without complex assertions"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_ingestion_source_basic(self):
        """Test basic IngestionSource functionality"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Test Source'
        )
        self.assertIsNotNone(source.id)
        self.assertEqual(source.user, self.user)
        self.assertEqual(source.source_type, 'image')
        self.assertEqual(source.source_name, 'Test Source')
        self.assertIsNotNone(source.created_at)
        self.assertFalse(source.is_test)
        self.assertIsNone(source.processed_at)
        
        # Test string representation
        str_repr = str(source)
        self.assertIn('Test Source', str_repr)
        self.assertIn('Image Upload', str_repr)
    
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
    
    def test_ingestion_source_with_url(self):
        """Test IngestionSource with URL"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='url',
            source_name='Test URL Source',
            source_url='https://example.com/recipe'
        )
        
        self.assertEqual(source.source_url, 'https://example.com/recipe')
        self.assertEqual(source.source_type, 'url')
    
    def test_ingestion_source_with_text(self):
        """Test IngestionSource with text content"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Text Source',
            raw_text='This is some recipe text content'
        )
        
        self.assertEqual(source.raw_text, 'This is some recipe text content')
        self.assertEqual(source.source_type, 'text')
    
    def test_ingestion_job_basic(self):
        """Test basic IngestionJob functionality"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Test Source'
        )
        
        job = IngestionJob.objects.create(
            source=source,
            status='pending'
        )
        
        self.assertIsNotNone(job.id)
        self.assertEqual(job.source, source)
        self.assertEqual(job.status, 'pending')
        self.assertIsNotNone(job.started_at)
        self.assertIsNone(job.completed_at)
        self.assertEqual(job.error_message, '')
        self.assertEqual(job.recipes_found, 0)
        self.assertEqual(job.recipes_processed, 0)
        
        # Test string representation
        str_repr = str(job)
        self.assertIn('Job', str_repr)
        self.assertIn('pending', str_repr)
    
    def test_ingestion_job_status_changes(self):
        """Test IngestionJob status field changes"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Test Source'
        )
        
        job = IngestionJob.objects.create(
            source=source,
            status='pending'
        )
        
        job.status = 'processing'
        job.save()
        self.assertEqual(job.status, 'processing')
        
        job.status = 'completed'
        job.save()
        self.assertEqual(job.status, 'completed')
    
    def test_extracted_recipe_basic(self):
        """Test basic ExtractedRecipe functionality"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Test Source'
        )
        
        job = IngestionJob.objects.create(
            source=source,
            status='pending'
        )
        
        recipe = ExtractedRecipe.objects.create(
            job=job,
            raw_name='Test Recipe',
            raw_ingredients=['ingredient 1', 'ingredient 2'],
            raw_instructions='Step 1, Step 2',
            confidence_score=0.85
        )
        
        self.assertIsNotNone(recipe.id)
        self.assertEqual(recipe.job, job)
        self.assertEqual(recipe.raw_name, 'Test Recipe')
        self.assertEqual(recipe.raw_ingredients, ['ingredient 1', 'ingredient 2'])
        self.assertEqual(recipe.raw_instructions, 'Step 1, Step 2')
        self.assertEqual(recipe.confidence_score, 0.85)
        self.assertIsNotNone(recipe.created_at)
        
        # Test string representation
        str_repr = str(recipe)
        self.assertIn('Extracted:', str_repr)
        self.assertIn('Test Recipe', str_repr)
    
    def test_multi_image_source_basic(self):
        """Test basic MultiImageSource functionality"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='multi_image',
            source_name='Test Multi Source'
        )
        
        file = SimpleUploadedFile(
            'page1.jpg',
            b'fake page content',
            content_type='image/jpeg'
        )
        
        multi_image = MultiImageSource.objects.create(
            source=source,
            page_number=1,
            page_type='ingredients',
            image_file=file
        )
        
        self.assertIsNotNone(multi_image.id)
        self.assertEqual(multi_image.source, source)
        self.assertEqual(multi_image.page_number, 1)
        self.assertEqual(multi_image.page_type, 'ingredients')
        self.assertIn('recipe_sources/multi/', multi_image.image_file.name)
        self.assertIn('page1', multi_image.image_file.name)
        self.assertIsNotNone(multi_image.created_at)
        
        # Test string representation
        str_repr = str(multi_image)
        self.assertIn('Page 1', str_repr)
        self.assertIn('Ingredients Page', str_repr)
    
    def test_processing_log_basic(self):
        """Test basic ProcessingLog functionality"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='image',
            source_name='Test Source'
        )
        
        job = IngestionJob.objects.create(
            source=source,
            status='pending'
        )
        
        log = ProcessingLog.objects.create(
            job=job,
            step='ocr_processing',
            level='info',
            message='OCR processing started'
        )
        
        self.assertIsNotNone(log.id)
        self.assertEqual(log.job, job)
        self.assertEqual(log.step, 'ocr_processing')
        self.assertEqual(log.level, 'info')
        self.assertEqual(log.message, 'OCR processing started')
        self.assertIsNotNone(log.created_at)
        
        # Test string representation
        str_repr = str(log)
        self.assertIn('ocr_processing', str_repr)
        self.assertIn('OCR processing started', str_repr)
    
    def test_recipe_template_basic(self):
        """Test basic RecipeTemplate functionality"""
        template = RecipeTemplate.objects.create(
            name='Test Template',
            description='A test recipe template',
            pattern='test pattern'
        )
        
        self.assertIsNotNone(template.id)
        self.assertEqual(template.name, 'Test Template')
        self.assertEqual(template.description, 'A test recipe template')
        self.assertEqual(template.pattern, 'test pattern')
        self.assertTrue(template.is_active)
        self.assertIsNotNone(template.created_at)
        
        # Test string representation
        str_repr = str(template)
        self.assertEqual(str_repr, 'Test Template')
    
    def test_approved_email_sender_basic(self):
        """Test basic ApprovedEmailSender functionality"""
        sender = ApprovedEmailSender.objects.create(
            email_address='test@example.com',
            sender_name='Test Sender'
        )
        
        self.assertIsNotNone(sender.id)
        self.assertEqual(sender.email_address, 'test@example.com')
        self.assertEqual(sender.sender_name, 'Test Sender')
        self.assertTrue(sender.is_active)
        self.assertIsNotNone(sender.created_at)
        self.assertIsNotNone(sender.updated_at)
        
        # Test string representation
        str_repr = str(sender)
        self.assertIn('test@example.com', str_repr)
        self.assertIn('Test Sender', str_repr)
    
    def test_approved_email_sender_no_name(self):
        """Test ApprovedEmailSender without name"""
        sender = ApprovedEmailSender.objects.create(
            email_address='test2@example.com'
        )
        
        self.assertEqual(sender.sender_name, '')
        
        # Test string representation
        str_repr = str(sender)
        self.assertEqual(str_repr, 'test2@example.com')
    
    def test_email_ingestion_source_basic(self):
        """Test basic EmailIngestionSource functionality"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='email',
            source_name='Test Email Source'
        )
        
        email_source = EmailIngestionSource.objects.create(
            source=source,
            sender_email='sender@example.com',
            sender_name='Test Sender',
            subject='Test Recipe Email',
            received_at='2025-01-01T00:00:00Z',
            message_id='test-message-123'
        )
        
        self.assertIsNotNone(email_source.id)
        self.assertEqual(email_source.source, source)
        self.assertEqual(email_source.sender_email, 'sender@example.com')
        self.assertEqual(email_source.sender_name, 'Test Sender')
        self.assertEqual(email_source.subject, 'Test Recipe Email')
        self.assertEqual(email_source.message_id, 'test-message-123')
        self.assertEqual(email_source.attachment_count, 0)
        self.assertFalse(email_source.is_approved_sender)
        self.assertIsNotNone(email_source.created_at)
        
        # Test string representation
        str_repr = str(email_source)
        self.assertIn('sender@example.com', str_repr)
        self.assertIn('Test Recipe Email', str_repr)
    
    def test_email_attachment_basic(self):
        """Test basic EmailAttachment functionality"""
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='email',
            source_name='Test Email Source'
        )
        
        email_source = EmailIngestionSource.objects.create(
            source=source,
            sender_email='sender@example.com',
            subject='Test Recipe Email',
            received_at='2025-01-01T00:00:00Z',
            message_id='test-message-123'
        )
        
        file = SimpleUploadedFile(
            'recipe.pdf',
            b'fake pdf content',
            content_type='application/pdf'
        )
        
        attachment = EmailAttachment.objects.create(
            email_source=email_source,
            filename='recipe.pdf',
            content_type='application/pdf',
            file_size=1024,
            attachment_file=file
        )
        
        self.assertIsNotNone(attachment.id)
        self.assertEqual(attachment.email_source, email_source)
        self.assertEqual(attachment.filename, 'recipe.pdf')
        self.assertEqual(attachment.content_type, 'application/pdf')
        self.assertEqual(attachment.file_size, 1024)
        self.assertIn('recipe_sources/email/', attachment.attachment_file.name)
        self.assertFalse(attachment.is_processed)
        self.assertEqual(attachment.attachment_type, 'attachment')
        self.assertIsNotNone(attachment.created_at)
        
        # Test string representation
        str_repr = str(attachment)
        self.assertIn('recipe.pdf', str_repr)
        self.assertIn('application/pdf', str_repr)
    
    def test_model_meta_options(self):
        """Test model Meta options"""
        # Test MultiImageSource ordering
        source = IngestionSource.objects.create(
            user=self.user,
            source_type='multi_image',
            source_name='Test Multi Source'
        )
        
        file1 = SimpleUploadedFile('page1.jpg', b'content1', content_type='image/jpeg')
        file2 = SimpleUploadedFile('page2.jpg', b'content2', content_type='image/jpeg')
        
        multi1 = MultiImageSource.objects.create(
            source=source, page_number=2, page_type='ingredients', image_file=file1
        )
        multi2 = MultiImageSource.objects.create(
            source=source, page_number=1, page_type='instructions', image_file=file2
        )
        
        # Should be ordered by page_number
        ordered = list(source.multi_images.all())
        self.assertEqual(ordered[0].page_number, 1)
        self.assertEqual(ordered[1].page_number, 2)
    
    def test_ingredient_mapping_basic(self):
        """Test basic IngredientMapping functionality (without foreign keys)"""
        mapping = IngredientMapping.objects.create(
            raw_text='tomato',
            confidence=0.9
        )
        
        self.assertIsNotNone(mapping.id)
        self.assertEqual(mapping.raw_text, 'tomato')
        self.assertEqual(mapping.confidence, 0.9)
        self.assertIsNone(mapping.normalized_ingredient)
        self.assertIsNone(mapping.quantity)
        self.assertIsNone(mapping.unit)
        self.assertEqual(mapping.preparation_method, '')
        self.assertIsNotNone(mapping.created_at)
        
        # Test string representation
        str_repr = str(mapping)
        self.assertIn('tomato', str_repr)
        self.assertIn('None', str_repr)  # normalized_ingredient is None
