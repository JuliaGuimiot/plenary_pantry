import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test.utils import override_settings

from recipe_ingestion.models import (
    IngestionSource, IngestionJob, ExtractedRecipe, 
    MultiImageSource, ProcessingLog, RecipeTemplate
)
from core.models import Recipe, Ingredient, Unit


class TestRecipeIngestionViews(TestCase):
    """Test the recipe ingestion views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
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
        
        # Login the user
        self.client.login(username='testuser', password='testpass123')
    
    def test_ingestion_dashboard_authenticated(self):
        """Test ingestion dashboard for authenticated user"""
        response = self.client.get(reverse('ingestion_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/dashboard.html')
        
        # Check context data
        self.assertIn('recent_sources', response.context)
        self.assertIn('recent_jobs', response.context)
        self.assertIn('total_sources', response.context)
        self.assertIn('total_jobs', response.context)
        self.assertIn('successful_jobs', response.context)
        self.assertIn('success_rate', response.context)
    
    def test_ingestion_dashboard_unauthenticated(self):
        """Test ingestion dashboard redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get(reverse('ingestion_dashboard'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_upload_image_get(self):
        """Test image upload form display"""
        response = self.client.get(reverse('upload_image'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/upload_image.html')
    
    def test_upload_image_post_valid(self):
        """Test valid image upload"""
        # Create a test image file
        image_file = SimpleUploadedFile(
            'test_recipe.jpg',
            b'fake image content',
            content_type='image/jpeg'
        )
        
        # Mock the service
        with patch('recipe_ingestion.views.RecipeIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock the job creation
            mock_job = Mock()
            mock_job.id = 'test-job-id'
            mock_service.process_source.return_value = mock_job
            
            response = self.client.post(reverse('upload_image'), {
                'recipe_image': image_file
            })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Image uploaded successfully', str(response.cookies))
    
    def test_upload_image_post_invalid_file_type(self):
        """Test image upload with invalid file type"""
        # Create an invalid file
        invalid_file = SimpleUploadedFile(
            'test.txt',
            b'not an image',
            content_type='text/plain'
        )
        
        response = self.client.post(reverse('upload_image'), {
            'recipe_image': invalid_file
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Please upload a valid image file', str(response.cookies))
    
    def test_upload_image_post_no_file(self):
        """Test image upload without file"""
        response = self.client.post(reverse('upload_image'), {})
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Please select an image file', str(response.cookies))
    
    def test_process_url_get(self):
        """Test URL processing form display"""
        response = self.client.get(reverse('process_url'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/process_url.html')
    
    def test_process_url_post_valid(self):
        """Test valid URL processing"""
        # Mock the service
        with patch('recipe_ingestion.views.RecipeIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock the job creation
            mock_job = Mock()
            mock_job.id = 'test-job-id'
            mock_service.process_source.return_value = mock_job
            
            response = self.client.post(reverse('process_url'), {
                'recipe_url': 'https://example.com/recipe'
            })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('URL processed successfully', str(response.cookies))
    
    def test_process_url_post_no_url(self):
        """Test URL processing without URL"""
        response = self.client.post(reverse('process_url'), {})
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Please provide a URL', str(response.cookies))
    
    def test_process_text_get(self):
        """Test text processing form display"""
        response = self.client.get(reverse('process_text'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/process_text.html')
    
    def test_process_text_post_valid(self):
        """Test valid text processing"""
        # Mock the service
        with patch('recipe_ingestion.views.RecipeIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock the job creation
            mock_job = Mock()
            mock_job.id = 'test-job-id'
            mock_service.process_source.return_value = mock_job
            
            response = self.client.post(reverse('process_text'), {
                'recipe_text': 'Test recipe text content'
            })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Text processed successfully', str(response.cookies))
    
    def test_process_text_post_no_text(self):
        """Test text processing without text"""
        response = self.client.post(reverse('process_text'), {})
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Please provide recipe text', str(response.cookies))
    
    def test_job_detail_authenticated(self):
        """Test job detail view for authenticated user"""
        response = self.client.get(reverse('job_detail', kwargs={'job_id': self.job.id}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/job_detail.html')
        
        # Check context data
        self.assertIn('job', response.context)
        self.assertIn('extracted_recipes', response.context)
        self.assertEqual(response.context['job'], self.job)
    
    def test_job_detail_unauthenticated(self):
        """Test job detail redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get(reverse('job_detail', kwargs={'job_id': self.job.id}))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_job_detail_not_found(self):
        """Test job detail with non-existent job"""
        response = self.client.get(reverse('job_detail', kwargs={'job_id': 'non-existent'}))
        
        self.assertEqual(response.status_code, 404)
    
    def test_job_detail_wrong_user(self):
        """Test job detail with job from different user"""
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
        
        other_job = IngestionJob.objects.create(source=other_source)
        
        response = self.client.get(reverse('job_detail', kwargs={'job_id': other_job.id}))
        
        self.assertEqual(response.status_code, 404)
    
    def test_email_history_authenticated(self):
        """Test email history view for authenticated user"""
        response = self.client.get(reverse('email_history'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/email_history.html')
    
    def test_email_history_unauthenticated(self):
        """Test email history redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get(reverse('email_history'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_email_mappings_authenticated(self):
        """Test email mappings view for authenticated user"""
        response = self.client.get(reverse('email_mappings'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/email_mappings.html')
    
    def test_email_mappings_unauthenticated(self):
        """Test email mappings redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get(reverse('email_mappings'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_mobile_upload_get(self):
        """Test mobile upload form display"""
        response = self.client.get(reverse('mobile_upload'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/mobile_upload.html')
    
    def test_mobile_upload_post_valid(self):
        """Test valid mobile upload"""
        # Create a test image file
        image_file = SimpleUploadedFile(
            'mobile_recipe.jpg',
            b'fake mobile image content',
            content_type='image/jpeg'
        )
        
        # Mock the service
        with patch('recipe_ingestion.views.RecipeIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock the job creation
            mock_job = Mock()
            mock_job.id = 'mobile-job-id'
            mock_service.process_source.return_value = mock_job
            
            response = self.client.post(reverse('mobile_upload'), {
                'recipe_image': image_file
            })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Mobile upload successful', str(response.cookies))
    
    def test_mobile_upload_post_no_file(self):
        """Test mobile upload without file"""
        response = self.client.post(reverse('mobile_upload'), {})
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Please select an image file', str(response.cookies))
    
    def test_mobile_upload_post_invalid_file_type(self):
        """Test mobile upload with invalid file type"""
        # Create an invalid file
        invalid_file = SimpleUploadedFile(
            'test.txt',
            b'not an image',
            content_type='text/plain'
        )
        
        response = self.client.post(reverse('mobile_upload'), {
            'recipe_image': invalid_file
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Please upload a valid image file', str(response.cookies))
    
    def test_upload_multi_image_get(self):
        """Test multi-image upload form display"""
        response = self.client.get(reverse('upload_multi_image'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/upload_multi_image.html')
    
    def test_upload_multi_image_post_valid(self):
        """Test valid multi-image upload"""
        # Create test image files
        image1 = SimpleUploadedFile(
            'page1.jpg',
            b'page 1 content',
            content_type='image/jpeg'
        )
        image2 = SimpleUploadedFile(
            'page2.jpg',
            b'page 2 content',
            content_type='image/jpeg'
        )
        
        # Mock the service
        with patch('recipe_ingestion.views.RecipeIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock the job creation
            mock_job = Mock()
            mock_job.id = 'multi-job-id'
            mock_service.process_source.return_value = mock_job
            
            response = self.client.post(reverse('upload_multi_image'), {
                'recipe_images': [image1, image2]
            })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Multi-image upload successful', str(response.cookies))
    
    def test_upload_multi_image_post_no_files(self):
        """Test multi-image upload without files"""
        response = self.client.post(reverse('upload_multi_image'), {})
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Please select image files', str(response.cookies))
    
    def test_upload_multi_image_post_invalid_file_type(self):
        """Test multi-image upload with invalid file type"""
        # Create an invalid file
        invalid_file = SimpleUploadedFile(
            'test.txt',
            b'not an image',
            content_type='text/plain'
        )
        
        response = self.client.post(reverse('upload_multi_image'), {
            'recipe_images': [invalid_file]
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Please upload valid image files', str(response.cookies))
    
    def test_recipe_templates_authenticated(self):
        """Test recipe templates view for authenticated user"""
        response = self.client.get(reverse('recipe_templates'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/recipe_templates.html')
    
    def test_recipe_templates_unauthenticated(self):
        """Test recipe templates redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get(reverse('recipe_templates'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_processing_logs_authenticated(self):
        """Test processing logs view for authenticated user"""
        response = self.client.get(reverse('processing_logs'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/processing_logs.html')
    
    def test_processing_logs_unauthenticated(self):
        """Test processing logs redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get(reverse('processing_logs'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_ingestion_statistics_authenticated(self):
        """Test ingestion statistics view for authenticated user"""
        response = self.client.get(reverse('ingestion_statistics'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/ingestion_statistics.html')
    
    def test_ingestion_statistics_unauthenticated(self):
        """Test ingestion statistics redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get(reverse('ingestion_statistics'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_bulk_ingestion_get(self):
        """Test bulk ingestion form display"""
        response = self.client.get(reverse('bulk_ingestion'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/bulk_ingestion.html')
    
    def test_bulk_ingestion_post_valid(self):
        """Test valid bulk ingestion"""
        # Create test files
        file1 = SimpleUploadedFile(
            'recipe1.jpg',
            b'recipe 1 content',
            content_type='image/jpeg'
        )
        file2 = SimpleUploadedFile(
            'recipe2.jpg',
            b'recipe 2 content',
            content_type='image/jpeg'
        )
        
        # Mock the service
        with patch('recipe_ingestion.views.RecipeIngestionService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock the job creation
            mock_job = Mock()
            mock_job.id = 'bulk-job-id'
            mock_service.process_source.return_value = mock_job
            
            response = self.client.post(reverse('bulk_ingestion'), {
                'recipe_files': [file1, file2]
            })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Bulk ingestion started', str(response.cookies))
    
    def test_bulk_ingestion_post_no_files(self):
        """Test bulk ingestion without files"""
        response = self.client.post(reverse('bulk_ingestion'), {})
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Please select files', str(response.cookies))
    
    def test_bulk_ingestion_post_invalid_file_type(self):
        """Test bulk ingestion with invalid file type"""
        # Create an invalid file
        invalid_file = SimpleUploadedFile(
            'test.txt',
            b'not an image',
            content_type='text/plain'
        )
        
        response = self.client.post(reverse('bulk_ingestion'), {
            'recipe_files': [invalid_file]
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Please upload valid image files', str(response.cookies))
    
    def test_ingestion_settings_authenticated(self):
        """Test ingestion settings view for authenticated user"""
        response = self.client.get(reverse('ingestion_settings'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/ingestion_settings.html')
    
    def test_ingestion_settings_unauthenticated(self):
        """Test ingestion settings redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get(reverse('ingestion_settings'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_ingestion_settings_post_valid(self):
        """Test valid ingestion settings update"""
        response = self.client.post(reverse('ingestion_settings'), {
            'auto_process': 'on',
            'confidence_threshold': '0.7',
            'max_ingredients': '20'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('Settings updated successfully', str(response.cookies))
    
    def test_ingestion_help_authenticated(self):
        """Test ingestion help view for authenticated user"""
        response = self.client.get(reverse('ingestion_help'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/ingestion_help.html')
    
    def test_ingestion_help_unauthenticated(self):
        """Test ingestion help redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get(reverse('ingestion_help'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_ingestion_api_docs_authenticated(self):
        """Test ingestion API docs view for authenticated user"""
        response = self.client.get(reverse('ingestion_api_docs'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/ingestion_api_docs.html')
    
    def test_ingestion_api_docs_unauthenticated(self):
        """Test ingestion API docs redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get(reverse('ingestion_api_docs'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
