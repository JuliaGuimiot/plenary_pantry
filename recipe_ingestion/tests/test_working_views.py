from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
import uuid

from recipe_ingestion.models import (
    IngestionSource, IngestionJob, ExtractedRecipe, 
    IngredientMapping, ProcessingLog
)

User = get_user_model()


class TestWorkingViews(TestCase):
    """Test the views that actually exist and work in recipe_ingestion"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test data
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
        
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
    
    def test_ingestion_dashboard_authenticated(self):
        """Test dashboard view when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_ingestion:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/dashboard.html')
    
    def test_ingestion_dashboard_unauthenticated(self):
        """Test dashboard view redirects when not authenticated"""
        response = self.client.get(reverse('recipe_ingestion:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/accounts/login/?next={reverse("recipe_ingestion:dashboard")}')
    
    def test_upload_image_get(self):
        """Test upload image GET request"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_ingestion:upload_image'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_ingestion/upload_image.html')
    
    def test_upload_image_post_valid(self):
        """Test upload image POST with valid file"""
        self.client.login(username='testuser', password='testpass123')
        
        with open('recipe_ingestion/tests/images/pudding_cakes.jpeg', 'rb') as f:
            file_data = f.read()
        
        uploaded_file = SimpleUploadedFile(
            'test_image.jpg',
            file_data,
            content_type='image/jpeg'
        )
        
        response = self.client.post(reverse('recipe_ingestion:upload_image'), {
            'recipe_image': uploaded_file
        })
        
        # Should redirect to dashboard or job detail
        self.assertIn(response.status_code, [200, 302])
    
    def test_upload_image_post_no_file(self):
        """Test upload image POST without file"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipe_ingestion:upload_image'), {})
        self.assertEqual(response.status_code, 302)  # Redirects back
    
    def test_process_url_get(self):
        """Test process URL GET request"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_ingestion:process_url'))
        self.assertEqual(response.status_code, 200)
    
    def test_process_url_post_valid(self):
        """Test process URL POST with valid URL"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipe_ingestion:process_url'), {
            'url': 'https://example.com/recipe'
        })
        self.assertIn(response.status_code, [200, 302])
    
    def test_process_url_post_no_url(self):
        """Test process URL POST without URL"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipe_ingestion:process_url'), {})
        self.assertEqual(response.status_code, 200)  # Stays on form
    
    def test_manual_input_get(self):
        """Test manual input GET request"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_ingestion:manual_input'))
        self.assertEqual(response.status_code, 200)
    
    def test_manual_input_post_valid(self):
        """Test manual input POST with valid data"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipe_ingestion:manual_input'), {
            'recipe_text': 'Test recipe text'
        })
        self.assertIn(response.status_code, [200, 302])
    
    def test_job_list_authenticated(self):
        """Test job list view when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_ingestion:job_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_job_list_unauthenticated(self):
        """Test job list view redirects when not authenticated"""
        response = self.client.get(reverse('recipe_ingestion:job_list'))
        self.assertEqual(response.status_code, 302)
    
    def test_job_detail_authenticated(self):
        """Test job detail view when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_ingestion:job_detail', kwargs={'job_id': self.job.id}))
        self.assertEqual(response.status_code, 200)
    
    def test_job_detail_unauthenticated(self):
        """Test job detail view redirects when not authenticated"""
        response = self.client.get(reverse('recipe_ingestion:job_detail', kwargs={'job_id': self.job.id}))
        self.assertEqual(response.status_code, 302)
    
    def test_job_detail_wrong_user(self):
        """Test job detail view denies access to wrong user"""
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(reverse('recipe_ingestion:job_detail', kwargs={'job_id': self.job.id}))
        self.assertEqual(response.status_code, 404)  # Job not found for this user
    
    def test_job_detail_not_found(self):
        """Test job detail view with non-existent job"""
        self.client.login(username='testuser', password='testpass123')
        fake_id = uuid.uuid4()
        response = self.client.get(reverse('recipe_ingestion:job_detail', kwargs={'job_id': fake_id}))
        self.assertEqual(response.status_code, 404)
    
    def test_mobile_upload_get(self):
        """Test mobile upload GET request"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_ingestion:mobile_upload'))
        self.assertEqual(response.status_code, 200)
    
    def test_mobile_upload_post_valid(self):
        """Test mobile upload POST with valid file"""
        self.client.login(username='testuser', password='testpass123')
        
        with open('recipe_ingestion/tests/images/pudding_cakes.jpeg', 'rb') as f:
            file_data = f.read()
        
        uploaded_file = SimpleUploadedFile(
            'mobile_image.jpg',
            file_data,
            content_type='image/jpeg'
        )
        
        response = self.client.post(reverse('recipe_ingestion:mobile_upload'), {
            'image': uploaded_file
        })
        
        self.assertIn(response.status_code, [200, 302])
    
    def test_ingredient_mappings_authenticated(self):
        """Test ingredient mappings view when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_ingestion:ingredient_mappings'))
        self.assertEqual(response.status_code, 200)
    
    def test_ingredient_mappings_unauthenticated(self):
        """Test ingredient mappings view redirects when not authenticated"""
        response = self.client.get(reverse('recipe_ingestion:ingredient_mappings'))
        self.assertEqual(response.status_code, 302)
    
    def test_email_mappings_authenticated(self):
        """Test email mappings view when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_ingestion:email_mappings'))
        self.assertEqual(response.status_code, 200)
    
    def test_email_mappings_unauthenticated(self):
        """Test email mappings view redirects when not authenticated"""
        response = self.client.get(reverse('recipe_ingestion:email_mappings'))
        self.assertEqual(response.status_code, 302)
    
    def test_email_history_authenticated(self):
        """Test email history view when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_ingestion:email_history'))
        self.assertEqual(response.status_code, 200)
    
    def test_email_history_unauthenticated(self):
        """Test email history view redirects when not authenticated"""
        response = self.client.get(reverse('recipe_ingestion:email_history'))
        self.assertEqual(response.status_code, 302)
    
    def test_api_process_source_authenticated(self):
        """Test API process source when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipe_ingestion:api_process_source'), {
            'source_type': 'text',
            'content': 'Test recipe content'
        })
        self.assertEqual(response.status_code, 200)
    
    def test_api_process_source_unauthenticated(self):
        """Test API process source redirects when not authenticated"""
        response = self.client.post(reverse('recipe_ingestion:api_process_source'), {
            'source_type': 'text',
            'content': 'Test recipe content'
        })
        self.assertEqual(response.status_code, 302)
    
    def test_api_job_status_authenticated(self):
        """Test API job status when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_ingestion:api_job_status', kwargs={'job_id': self.job.id}))
        self.assertEqual(response.status_code, 200)
    
    def test_api_job_status_unauthenticated(self):
        """Test API job status redirects when not authenticated"""
        response = self.client.get(reverse('recipe_ingestion:api_job_status', kwargs={'job_id': self.job.id}))
        self.assertEqual(response.status_code, 302)
    
    def test_delete_job_authenticated(self):
        """Test delete job when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipe_ingestion:delete_job', kwargs={'job_id': self.job.id}))
        self.assertEqual(response.status_code, 302)  # Redirects after deletion
    
    def test_delete_job_unauthenticated(self):
        """Test delete job redirects when not authenticated"""
        response = self.client.post(reverse('recipe_ingestion:delete_job', kwargs={'job_id': self.job.id}))
        self.assertEqual(response.status_code, 302)
    
    def test_delete_job_wrong_user(self):
        """Test delete job denies access to wrong user"""
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.post(reverse('recipe_ingestion:delete_job', kwargs={'job_id': self.job.id}))
        self.assertEqual(response.status_code, 404)  # Job not found for this user
