import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.admin.sites import AdminSite

from recipe_ingestion.admin import (
    IngestionSourceAdmin, IngestionJobAdmin, ExtractedRecipeAdmin,
    MultiImageSourceAdmin, ProcessingLogAdmin, RecipeTemplateAdmin,
    IngredientMappingAdmin, ApprovedEmailSenderAdmin, EmailIngestionSourceAdmin,
    EmailAttachmentAdmin
)
from recipe_ingestion.models import (
    IngestionSource, IngestionJob, ExtractedRecipe, 
    MultiImageSource, ProcessingLog, RecipeTemplate,
    IngredientMapping, ApprovedEmailSender, EmailIngestionSource,
    EmailAttachment
)
from core.models import Recipe, Ingredient, Unit


class TestIngestionSourceAdmin(TestCase):
    """Test the IngestionSourceAdmin class"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_site = AdminSite()
        self.admin = IngestionSourceAdmin(IngestionSource, self.admin_site)
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.source = IngestionSource.objects.create(
            user=self.user,
            source_type='text',
            source_name='Test Recipe',
            raw_text='Test recipe content'
        )
    
    def test_list_display(self):
        """Test list display fields"""
        expected_fields = [
            'source_name', 'user', 'source_type', 'processing_status',
            'created_at', 'processed_at'
        ]
        
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_list_filter(self):
        """Test list filter fields"""
        expected_filters = [
            'source_type', 'processing_status', 'created_at', 'processed_at'
        ]
        
        self.assertEqual(list(self.admin.list_filter), expected_filters)
    
    def test_search_fields(self):
        """Test search fields"""
        expected_search = [
            'source_name', 'raw_text', 'user__username', 'user__email'
        ]
        
        self.assertEqual(list(self.admin.search_fields), expected_search)
    
    def test_readonly_fields(self):
        """Test readonly fields"""
        expected_readonly = ['created_at', 'updated_at']
        
        self.assertEqual(list(self.admin.readonly_fields), expected_readonly)
    
    def test_date_hierarchy(self):
        """Test date hierarchy field"""
        self.assertEqual(self.admin.date_hierarchy, 'created_at')
    
    def test_ordering(self):
        """Test ordering"""
        expected_ordering = ['-created_at']
        
        self.assertEqual(list(self.admin.ordering), expected_ordering)
    
    def test_autocomplete_fields(self):
        """Test autocomplete fields"""
        expected_autocomplete = ['user']
        
        self.assertEqual(list(self.admin.autocomplete_fields), expected_autocomplete)
    
    def test_get_queryset(self):
        """Test queryset filtering"""
        # Create another user's source
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        other_source = IngestionSource.objects.create(
            user=other_user,
            source_type='text',
            source_name='Other Recipe'
        )
        
        # Test that admin can see all sources (no filtering)
        queryset = self.admin.get_queryset(self.client.request)
        self.assertIn(self.source, queryset)
        self.assertIn(other_source, queryset)


class TestIngestionJobAdmin(TestCase):
    """Test the IngestionJobAdmin class"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_site = AdminSite()
        self.admin = IngestionJobAdmin(IngestionJob, self.admin_site)
        
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
    
    def test_list_display(self):
        """Test list display fields"""
        expected_fields = [
            'id', 'source', 'status', 'recipes_found', 'recipes_processed',
            'created_at', 'started_at', 'completed_at'
        ]
        
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_list_filter(self):
        """Test list filter fields"""
        expected_filters = [
            'status', 'created_at', 'started_at', 'completed_at'
        ]
        
        self.assertEqual(list(self.admin.list_filter), expected_filters)
    
    def test_search_fields(self):
        """Test search fields"""
        expected_search = [
            'source__source_name', 'source__user__username', 'error_message'
        ]
        
        self.assertEqual(list(self.admin.search_fields), expected_search)
    
    def test_readonly_fields(self):
        """Test readonly fields"""
        expected_readonly = ['created_at', 'started_at', 'completed_at']
        
        self.assertEqual(list(self.admin.readonly_fields), expected_readonly)
    
    def test_date_hierarchy(self):
        """Test date hierarchy field"""
        self.assertEqual(self.admin.date_hierarchy, 'created_at')
    
    def test_ordering(self):
        """Test ordering"""
        expected_ordering = ['-created_at']
        
        self.assertEqual(list(self.admin.ordering), expected_ordering)
    
    def test_autocomplete_fields(self):
        """Test autocomplete fields"""
        expected_autocomplete = ['source']
        
        self.assertEqual(list(self.admin.autocomplete_fields), expected_autocomplete)
    
    def test_actions(self):
        """Test admin actions"""
        expected_actions = ['retry_failed_jobs', 'cancel_pending_jobs']
        
        self.assertEqual(list(self.admin.actions), expected_actions)
    
    def test_retry_failed_jobs_action(self):
        """Test retry failed jobs action"""
        # Create a failed job
        failed_job = IngestionJob.objects.create(
            source=self.source,
            status='failed',
            error_message='Test error'
        )
        
        # Test the action
        self.admin.retry_failed_jobs(self.admin, IngestionJob.objects.filter(status='failed'))
        
        # Check that job was reset
        failed_job.refresh_from_db()
        self.assertEqual(failed_job.status, 'pending')
        self.assertIsNone(failed_job.error_message)
    
    def test_cancel_pending_jobs_action(self):
        """Test cancel pending jobs action"""
        # Create a pending job
        pending_job = IngestionJob.objects.create(
            source=self.source,
            status='pending'
        )
        
        # Test the action
        self.admin.cancel_pending_jobs(self.admin, IngestionJob.objects.filter(status='pending'))
        
        # Check that job was cancelled
        pending_job.refresh_from_db()
        self.assertEqual(pending_job.status, 'cancelled')


class TestExtractedRecipeAdmin(TestCase):
    """Test the ExtractedRecipeAdmin class"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_site = AdminSite()
        self.admin = ExtractedRecipeAdmin(ExtractedRecipe, self.admin_site)
        
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
        
        self.extracted = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Test Recipe',
            confidence_score=0.85
        )
    
    def test_list_display(self):
        """Test list display fields"""
        expected_fields = [
            'raw_name', 'job', 'confidence_score', 'normalized_recipe',
            'created_at', 'normalized_at'
        ]
        
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_list_filter(self):
        """Test list filter fields"""
        expected_filters = [
            'confidence_score', 'created_at', 'normalized_at'
        ]
        
        self.assertEqual(list(self.admin.list_filter), expected_filters)
    
    def test_search_fields(self):
        """Test search fields"""
        expected_search = [
            'raw_name', 'raw_instructions', 'job__source__source_name'
        ]
        
        self.assertEqual(list(self.admin.search_fields), expected_search)
    
    def test_readonly_fields(self):
        """Test readonly fields"""
        expected_readonly = ['created_at', 'normalized_at']
        
        self.assertEqual(list(self.admin.readonly_fields), expected_readonly)
    
    def test_autocomplete_fields(self):
        """Test autocomplete fields"""
        expected_autocomplete = ['job', 'normalized_recipe']
        
        self.assertEqual(list(self.admin.autocomplete_fields), expected_autocomplete)
    
    def test_ordering(self):
        """Test ordering"""
        expected_ordering = ['-created_at']
        
        self.assertEqual(list(self.admin.ordering), expected_ordering)


class TestMultiImageSourceAdmin(TestCase):
    """Test the MultiImageSourceAdmin class"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_site = AdminSite()
        self.admin = MultiImageSourceAdmin(MultiImageSource, self.admin_site)
        
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
        
        self.multi_image = MultiImageSource.objects.create(
            source=self.source,
            page_number=1,
            page_type='recipe'
        )
    
    def test_list_display(self):
        """Test list display fields"""
        expected_fields = [
            'source', 'page_number', 'page_type', 'extracted_text_preview',
            'created_at'
        ]
        
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_list_filter(self):
        """Test list filter fields"""
        expected_filters = ['page_type', 'created_at']
        
        self.assertEqual(list(self.admin.list_filter), expected_filters)
    
    def test_search_fields(self):
        """Test search fields"""
        expected_search = [
            'source__source_name', 'extracted_text'
        ]
        
        self.assertEqual(list(self.admin.search_fields), expected_search)
    
    def test_readonly_fields(self):
        """Test readonly fields"""
        expected_readonly = ['created_at']
        
        self.assertEqual(list(self.admin.readonly_fields), expected_readonly)
    
    def test_autocomplete_fields(self):
        """Test autocomplete fields"""
        expected_autocomplete = ['source']
        
        self.assertEqual(list(self.admin.autocomplete_fields), expected_autocomplete)
    
    def test_extracted_text_preview(self):
        """Test extracted text preview method"""
        # Test with short text
        self.multi_image.extracted_text = 'Short text'
        self.multi_image.save()
        
        preview = self.admin.extracted_text_preview(self.multi_image)
        self.assertEqual(preview, 'Short text')
        
        # Test with long text
        long_text = 'This is a very long text that should be truncated to show only the first part and add ellipsis at the end to indicate there is more content'
        self.multi_image.extracted_text = long_text
        self.multi_image.save()
        
        preview = self.admin.extracted_text_preview(self.multi_image)
        self.assertIn('...', preview)
        self.assertLess(len(preview), len(long_text))


class TestProcessingLogAdmin(TestCase):
    """Test the ProcessingLogAdmin class"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_site = AdminSite()
        self.admin = ProcessingLogAdmin(ProcessingLog, self.admin_site)
        
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
        
        self.log = ProcessingLog.objects.create(
            job=self.job,
            step='test_step',
            level='info',
            message='Test message'
        )
    
    def test_list_display(self):
        """Test list display fields"""
        expected_fields = [
            'timestamp', 'job', 'step', 'level', 'message_preview'
        ]
        
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_list_filter(self):
        """Test list filter fields"""
        expected_filters = ['level', 'step', 'timestamp']
        
        self.assertEqual(list(self.admin.list_filter), expected_filters)
    
    def test_search_fields(self):
        """Test search fields"""
        expected_search = [
            'message', 'job__source__source_name'
        ]
        
        self.assertEqual(list(self.admin.search_fields), expected_search)
    
    def test_readonly_fields(self):
        """Test readonly fields"""
        expected_readonly = ['timestamp']
        
        self.assertEqual(list(self.admin.readonly_fields), expected_readonly)
    
    def test_ordering(self):
        """Test ordering"""
        expected_ordering = ['-timestamp']
        
        self.assertEqual(list(self.admin.ordering), expected_ordering)
    
    def test_message_preview(self):
        """Test message preview method"""
        # Test with short message
        self.log.message = 'Short message'
        self.log.save()
        
        preview = self.admin.message_preview(self.log)
        self.assertEqual(preview, 'Short message')
        
        # Test with long message
        long_message = 'This is a very long message that should be truncated to show only the first part and add ellipsis at the end to indicate there is more content'
        self.log.message = long_message
        self.log.save()
        
        preview = self.admin.message_preview(self.log)
        self.assertIn('...', preview)
        self.assertLess(len(preview), len(long_message))


class TestRecipeTemplateAdmin(TestCase):
    """Test the RecipeTemplateAdmin class"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_site = AdminSite()
        self.admin = RecipeTemplateAdmin(RecipeTemplate, self.admin_site)
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.template = RecipeTemplate.objects.create(
            user=self.user,
            name='Test Template',
            description='Test description'
        )
    
    def test_list_display(self):
        """Test list display fields"""
        expected_fields = [
            'name', 'user', 'is_active', 'usage_count', 'created_at'
        ]
        
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_list_filter(self):
        """Test list filter fields"""
        expected_filters = ['is_active', 'created_at']
        
        self.assertEqual(list(self.admin.list_filter), expected_filters)
    
    def test_search_fields(self):
        """Test search fields"""
        expected_search = [
            'name', 'description', 'user__username'
        ]
        
        self.assertEqual(list(self.admin.search_fields), expected_search)
    
    def test_readonly_fields(self):
        """Test readonly fields"""
        expected_readonly = ['created_at', 'usage_count']
        
        self.assertEqual(list(self.admin.readonly_fields), expected_readonly)
    
    def test_autocomplete_fields(self):
        """Test autocomplete fields"""
        expected_autocomplete = ['user']
        
        self.assertEqual(list(self.admin.autocomplete_fields), expected_autocomplete)
    
    def test_ordering(self):
        """Test ordering"""
        expected_ordering = ['-created_at']
        
        self.assertEqual(list(self.admin.ordering), expected_ordering)


class TestIngredientMappingAdmin(TestCase):
    """Test the IngredientMappingAdmin class"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_site = AdminSite()
        self.admin = IngredientMappingAdmin(IngredientMapping, self.admin_site)
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.ingredient = Ingredient.objects.create(
            name='all-purpose flour',
            description='Standard baking flour'
        )
        
        self.mapping = IngredientMapping.objects.create(
            user=self.user,
            raw_text='AP flour',
            normalized_ingredient=self.ingredient,
            confidence_score=0.9
        )
    
    def test_list_display(self):
        """Test list display fields"""
        expected_fields = [
            'raw_text', 'normalized_ingredient', 'user', 'confidence_score',
            'created_at'
        ]
        
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_list_filter(self):
        """Test list filter fields"""
        expected_filters = ['confidence_score', 'created_at']
        
        self.assertEqual(list(self.admin.list_filter), expected_filters)
    
    def test_search_fields(self):
        """Test search fields"""
        expected_search = [
            'raw_text', 'normalized_ingredient__name', 'user__username'
        ]
        
        self.assertEqual(list(self.admin.search_fields), expected_search)
    
    def test_readonly_fields(self):
        """Test readonly fields"""
        expected_readonly = ['created_at']
        
        self.assertEqual(list(self.admin.readonly_fields), expected_readonly)
    
    def test_autocomplete_fields(self):
        """Test autocomplete fields"""
        expected_autocomplete = ['user', 'normalized_ingredient']
        
        self.assertEqual(list(self.admin.autocomplete_fields), expected_autocomplete)
    
    def test_ordering(self):
        """Test ordering"""
        expected_ordering = ['-created_at']
        
        self.assertEqual(list(self.admin.ordering), expected_ordering)


class TestApprovedEmailSenderAdmin(TestCase):
    """Test the ApprovedEmailSenderAdmin class"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_site = AdminSite()
        self.admin = ApprovedEmailSenderAdmin(ApprovedEmailSender, self.admin_site)
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.sender = ApprovedEmailSender.objects.create(
            user=self.user,
            email_address='recipe@example.com',
            sender_name='Recipe Service'
        )
    
    def test_list_display(self):
        """Test list display fields"""
        expected_fields = [
            'sender_name', 'email_address', 'user', 'is_active', 'created_at'
        ]
        
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_list_filter(self):
        """Test list filter fields"""
        expected_filters = ['is_active', 'created_at']
        
        self.assertEqual(list(self.admin.list_filter), expected_filters)
    
    def test_search_fields(self):
        """Test search fields"""
        expected_search = [
            'sender_name', 'email_address', 'user__username'
        ]
        
        self.assertEqual(list(self.admin.search_fields), expected_search)
    
    def test_readonly_fields(self):
        """Test readonly fields"""
        expected_readonly = ['created_at']
        
        self.assertEqual(list(self.admin.readonly_fields), expected_readonly)
    
    def test_autocomplete_fields(self):
        """Test autocomplete fields"""
        expected_autocomplete = ['user']
        
        self.assertEqual(list(self.admin.autocomplete_fields), expected_autocomplete)
    
    def test_ordering(self):
        """Test ordering"""
        expected_ordering = ['-created_at']
        
        self.assertEqual(list(self.admin.ordering), expected_ordering)


class TestEmailIngestionSourceAdmin(TestCase):
    """Test the EmailIngestionSourceAdmin class"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_site = AdminSite()
        self.admin = EmailIngestionSourceAdmin(EmailIngestionSource, self.admin_site)
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.email_source = EmailIngestionSource.objects.create(
            user=self.user,
            email_subject='Test Recipe',
            sender_email='test@example.com',
            sender_name='Test Sender'
        )
    
    def test_list_display(self):
        """Test list display fields"""
        expected_fields = [
            'email_subject', 'sender_name', 'sender_email', 'user',
            'processing_status', 'received_at', 'processed_at'
        ]
        
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_list_filter(self):
        """Test list filter fields"""
        expected_filters = [
            'processing_status', 'received_at', 'processed_at'
        ]
        
        self.assertEqual(list(self.admin.list_filter), expected_filters)
    
    def test_search_fields(self):
        """Test search fields"""
        expected_search = [
            'email_subject', 'sender_name', 'sender_email', 'user__username'
        ]
        
        self.assertEqual(list(self.admin.search_fields), expected_search)
    
    def test_readonly_fields(self):
        """Test readonly fields"""
        expected_readonly = ['received_at', 'created_at']
        
        self.assertEqual(list(self.admin.readonly_fields), expected_readonly)
    
    def test_autocomplete_fields(self):
        """Test autocomplete fields"""
        expected_autocomplete = ['user']
        
        self.assertEqual(list(self.admin.autocomplete_fields), expected_autocomplete)
    
    def test_date_hierarchy(self):
        """Test date hierarchy field"""
        self.assertEqual(self.admin.date_hierarchy, 'received_at')
    
    def test_ordering(self):
        """Test ordering"""
        expected_ordering = ['-received_at']
        
        self.assertEqual(list(self.admin.ordering), expected_ordering)


class TestEmailAttachmentAdmin(TestCase):
    """Test the EmailAttachmentAdmin class"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_site = AdminSite()
        self.admin = EmailAttachmentAdmin(EmailAttachment, self.admin_site)
        
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
        
        self.attachment = EmailAttachment.objects.create(
            email_source=self.email_source,
            filename='recipe.jpg',
            content_type='image/jpeg',
            file_size=1024
        )
    
    def test_list_display(self):
        """Test list display fields"""
        expected_fields = [
            'filename', 'email_source', 'content_type', 'file_size',
            'processing_status', 'created_at', 'processed_at'
        ]
        
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_list_filter(self):
        """Test list filter fields"""
        expected_filters = [
            'content_type', 'processing_status', 'created_at', 'processed_at'
        ]
        
        self.assertEqual(list(self.admin.list_filter), expected_filters)
    
    def test_search_fields(self):
        """Test search fields"""
        expected_search = [
            'filename', 'email_source__email_subject'
        ]
        
        self.assertEqual(list(self.admin.search_fields), expected_search)
    
    def test_readonly_fields(self):
        """Test readonly fields"""
        expected_readonly = ['created_at']
        
        self.assertEqual(list(self.admin.readonly_fields), expected_readonly)
    
    def test_autocomplete_fields(self):
        """Test autocomplete fields"""
        expected_autocomplete = ['email_source']
        
        self.assertEqual(list(self.admin.autocomplete_fields), expected_autocomplete)
    
    def test_ordering(self):
        """Test ordering"""
        expected_ordering = ['-created_at']
        
        self.assertEqual(list(self.admin.ordering), expected_ordering)
