from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import site
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from recipe_ingestion.models import (
    IngestionSource, IngestionJob, ExtractedRecipe, 
    IngredientMapping, ProcessingLog, MultiImageSource
)
from recipe_ingestion.admin import (
    IngestionSourceAdmin, IngestionJobAdmin, ExtractedRecipeAdmin,
    MultiImageSourceAdmin, ProcessingLogAdmin, IngredientMappingAdmin
)

User = get_user_model()


class TestWorkingAdmin(TestCase):
    """Test the admin functionality that actually exists and works in recipe_ingestion"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
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
        
        self.recipe = ExtractedRecipe.objects.create(
            job=self.job,
            raw_name='Test Recipe',
            raw_ingredients='Test ingredients',
            raw_instructions='Test instructions',
            confidence_score=0.85
        )
        
        self.log = ProcessingLog.objects.create(
            job=self.job,
            step='general',
            level='info',
            message='Test log message'
        )
        
        self.mapping = IngredientMapping.objects.create(
            raw_ingredient='tomato',
            normalized_ingredient='tomato',
            confidence_score=0.9
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_admin_site_registration(self):
        """Test that models are registered in admin site"""
        self.assertIn(IngestionSource, site._registry)
        self.assertIn(IngestionJob, site._registry)
        self.assertIn(ExtractedRecipe, site._registry)
        self.assertIn(ProcessingLog, site._registry)
        self.assertIn(IngredientMapping, site._registry)
    
    def test_ingestion_source_admin_list_display(self):
        """Test IngestionSourceAdmin list_display"""
        admin = IngestionSourceAdmin(IngestionSource, site)
        expected_fields = ['source_name', 'source_type', 'user', 'created_at', 'processed_at']
        self.assertEqual(list(admin.list_display), expected_fields)
    
    def test_ingestion_source_admin_list_filter(self):
        """Test IngestionSourceAdmin list_filter"""
        admin = IngestionSourceAdmin(IngestionSource, site)
        expected_filters = ['source_type', 'is_test', 'created_at', 'processed_at']
        self.assertEqual(list(admin.list_filter), expected_filters)
    
    def test_ingestion_source_admin_search_fields(self):
        """Test IngestionSourceAdmin search_fields"""
        admin = IngestionSourceAdmin(IngestionSource, site)
        expected_fields = ['source_name', 'raw_content']
        self.assertEqual(list(admin.search_fields), expected_fields)
    
    def test_ingestion_source_admin_readonly_fields(self):
        """Test IngestionSourceAdmin readonly_fields"""
        admin = IngestionSourceAdmin(IngestionSource, site)
        expected_fields = ['created_at', 'updated_at']
        self.assertEqual(list(admin.readonly_fields), expected_fields)
    
    def test_ingestion_source_admin_date_hierarchy(self):
        """Test IngestionSourceAdmin date_hierarchy"""
        admin = IngestionSourceAdmin(IngestionSource, site)
        self.assertEqual(admin.date_hierarchy, 'created_at')
    
    def test_ingestion_source_admin_ordering(self):
        """Test IngestionSourceAdmin ordering"""
        admin = IngestionSourceAdmin(IngestionSource, site)
        expected_ordering = ['-created_at']
        self.assertEqual(list(admin.ordering), expected_ordering)
    
    def test_ingestion_job_admin_list_display(self):
        """Test IngestionJobAdmin list_display"""
        admin = IngestionJobAdmin(IngestionJob, site)
        expected_fields = ['id', 'source', 'status', 'recipes_found', 'recipes_processed', 'started_at', 'completed_at']
        self.assertEqual(list(admin.list_display), expected_fields)
    
    def test_ingestion_job_admin_list_filter(self):
        """Test IngestionJobAdmin list_filter"""
        admin = IngestionJobAdmin(IngestionJob, site)
        expected_filters = ['status', 'created_at', 'started_at', 'completed_at']
        self.assertEqual(list(admin.list_filter), expected_filters)
    
    def test_ingestion_job_admin_search_fields(self):
        """Test IngestionJobAdmin search_fields"""
        admin = IngestionJobAdmin(IngestionJob, site)
        expected_fields = ['source__source_name', 'source__user__username']
        self.assertEqual(list(admin.search_fields), expected_fields)
    
    def test_ingestion_job_admin_readonly_fields(self):
        """Test IngestionJobAdmin readonly_fields"""
        admin = IngestionJobAdmin(IngestionJob, site)
        expected_fields = ['created_at', 'started_at', 'completed_at']
        self.assertEqual(list(admin.readonly_fields), expected_fields)
    
    def test_ingestion_job_admin_date_hierarchy(self):
        """Test IngestionJobAdmin date_hierarchy"""
        admin = IngestionJobAdmin(IngestionJob, site)
        self.assertEqual(admin.date_hierarchy, 'created_at')
    
    def test_ingestion_job_admin_ordering(self):
        """Test IngestionJobAdmin ordering"""
        admin = IngestionJobAdmin(IngestionJob, site)
        expected_ordering = ['-created_at']
        self.assertEqual(list(admin.ordering), expected_ordering)
    
    def test_extracted_recipe_admin_list_display(self):
        """Test ExtractedRecipeAdmin list_display"""
        admin = ExtractedRecipeAdmin(ExtractedRecipe, site)
        expected_fields = ['raw_name', 'confidence_score', 'normalized_at', 'created_at']
        self.assertEqual(list(admin.list_display), expected_fields)
    
    def test_extracted_recipe_admin_list_filter(self):
        """Test ExtractedRecipeAdmin list_filter"""
        admin = ExtractedRecipeAdmin(ExtractedRecipe, site)
        expected_filters = ['confidence_score', 'created_at', 'normalized_at']
        self.assertEqual(list(admin.list_filter), expected_filters)
    
    def test_extracted_recipe_admin_search_fields(self):
        """Test ExtractedRecipeAdmin search_fields"""
        admin = ExtractedRecipeAdmin(ExtractedRecipe, site)
        expected_fields = ['raw_name', 'raw_ingredients', 'raw_instructions']
        self.assertEqual(list(admin.search_fields), expected_fields)
    
    def test_extracted_recipe_admin_readonly_fields(self):
        """Test ExtractedRecipeAdmin readonly_fields"""
        admin = ExtractedRecipeAdmin(ExtractedRecipe, site)
        expected_fields = ['created_at', 'normalized_at']
        self.assertEqual(list(admin.readonly_fields), expected_fields)
    
    def test_extracted_recipe_admin_ordering(self):
        """Test ExtractedRecipeAdmin ordering"""
        admin = ExtractedRecipeAdmin(ExtractedRecipe, site)
        expected_ordering = ['-created_at']
        self.assertEqual(list(admin.ordering), expected_ordering)
    
    def test_processing_log_admin_list_display(self):
        """Test ProcessingLogAdmin list_display"""
        admin = ProcessingLogAdmin(ProcessingLog, site)
        expected_fields = ['timestamp', 'job', 'step', 'level', 'created_at']
        self.assertEqual(list(admin.list_display), expected_fields)
    
    def test_processing_log_admin_list_filter(self):
        """Test ProcessingLogAdmin list_filter"""
        admin = ProcessingLogAdmin(ProcessingLog, site)
        expected_filters = ['level', 'step', 'timestamp']
        self.assertEqual(list(admin.list_filter), expected_filters)
    
    def test_processing_log_admin_search_fields(self):
        """Test ProcessingLogAdmin search_fields"""
        admin = ProcessingLogAdmin(ProcessingLog, site)
        expected_fields = ['message', 'job__source__source_name']
        self.assertEqual(list(admin.search_fields), expected_fields)
    
    def test_processing_log_admin_readonly_fields(self):
        """Test ProcessingLogAdmin readonly_fields"""
        admin = ProcessingLogAdmin(ProcessingLog, site)
        expected_fields = ['timestamp']
        self.assertEqual(list(admin.readonly_fields), expected_fields)
    
    def test_processing_log_admin_ordering(self):
        """Test ProcessingLogAdmin ordering"""
        admin = ProcessingLogAdmin(ProcessingLog, site)
        expected_ordering = ['-timestamp']
        self.assertEqual(list(admin.ordering), expected_ordering)
    
    def test_multi_image_source_admin_list_display(self):
        """Test MultiImageSourceAdmin list_display"""
        admin = MultiImageSourceAdmin(MultiImageSource, site)
        expected_fields = ['source', 'page_number', 'page_type', 'created_at']
        self.assertEqual(list(admin.list_display), expected_fields)
    
    def test_multi_image_source_admin_search_fields(self):
        """Test MultiImageSourceAdmin search_fields"""
        admin = MultiImageSourceAdmin(MultiImageSource, site)
        expected_fields = ['source__source_name', 'extracted_text']
        self.assertEqual(list(admin.search_fields), expected_fields)
    
    def test_multi_image_source_admin_readonly_fields(self):
        """Test MultiImageSourceAdmin readonly_fields"""
        admin = MultiImageSourceAdmin(MultiImageSource, site)
        expected_fields = ['created_at']
        self.assertEqual(list(admin.readonly_fields), expected_fields)
    
    def test_ingredient_mapping_admin_list_display(self):
        """Test IngredientMappingAdmin list_display"""
        admin = IngredientMappingAdmin(IngredientMapping, site)
        expected_fields = ['raw_ingredient', 'normalized_ingredient', 'confidence_score', 'created_at']
        self.assertEqual(list(admin.list_display), expected_fields)
    
    def test_ingredient_mapping_admin_list_filter(self):
        """Test IngredientMappingAdmin list_filter"""
        admin = IngredientMappingAdmin(IngredientMapping, site)
        expected_filters = ['confidence_score', 'created_at']
        self.assertEqual(list(admin.list_filter), expected_filters)
    
    def test_ingredient_mapping_admin_search_fields(self):
        """Test IngredientMappingAdmin search_fields"""
        admin = IngredientMappingAdmin(IngredientMapping, site)
        expected_fields = ['raw_ingredient', 'normalized_ingredient']
        self.assertEqual(list(admin.search_fields), expected_fields)
    
    def test_ingredient_mapping_admin_readonly_fields(self):
        """Test IngredientMappingAdmin readonly_fields"""
        admin = IngredientMappingAdmin(IngredientMapping, site)
        expected_fields = ['created_at', 'updated_at']
        self.assertEqual(list(admin.readonly_fields), expected_fields)
    
    def test_ingredient_mapping_admin_ordering(self):
        """Test IngredientMappingAdmin ordering"""
        admin = IngredientMappingAdmin(IngredientMapping, site)
        expected_ordering = ['-created_at']
        self.assertEqual(list(admin.ordering), expected_ordering)
    
    def test_admin_changelist_views(self):
        """Test that admin changelist views are accessible"""
        # Test IngestionSource changelist
        response = self.client.get(reverse('admin:recipe_ingestion_ingestionsource_changelist'))
        self.assertEqual(response.status_code, 200)
        
        # Test IngestionJob changelist
        response = self.client.get(reverse('admin:recipe_ingestion_ingestionjob_changelist'))
        self.assertEqual(response.status_code, 200)
        
        # Test ExtractedRecipe changelist
        response = self.client.get(reverse('admin:recipe_ingestion_extractedrecipe_changelist'))
        self.assertEqual(response.status_code, 200)
        
        # Test ProcessingLog changelist
        response = self.client.get(reverse('admin:recipe_ingestion_processinglog_changelist'))
        self.assertEqual(response.status_code, 200)
        
        # Test IngredientMapping changelist
        response = self.client.get(reverse('admin:recipe_ingestion_ingredientmapping_changelist'))
        self.assertEqual(response.status_code, 200)
    
    def test_admin_change_views(self):
        """Test that admin change views are accessible"""
        # Test IngestionSource change
        response = self.client.get(reverse('admin:recipe_ingestion_ingestionsource_change', args=[self.source.id]))
        self.assertEqual(response.status_code, 200)
        
        # Test IngestionJob change
        response = self.client.get(reverse('admin:recipe_ingestion_ingestionjob_change', args=[self.job.id]))
        self.assertEqual(response.status_code, 200)
        
        # Test ExtractedRecipe change
        response = self.client.get(reverse('admin:recipe_ingestion_extractedrecipe_change', args=[self.recipe.id]))
        self.assertEqual(response.status_code, 200)
        
        # Test ProcessingLog change
        response = self.client.get(reverse('admin:recipe_ingestion_processinglog_change', args=[self.log.id]))
        self.assertEqual(response.status_code, 200)
        
        # Test IngredientMapping change
        response = self.client.get(reverse('admin:recipe_ingestion_ingredientmapping_change', args=[self.mapping.id]))
        self.assertEqual(response.status_code, 200)
    
    def test_admin_add_views(self):
        """Test that admin add views are accessible"""
        # Test IngestionSource add
        response = self.client.get(reverse('admin:recipe_ingestion_ingestionsource_add'))
        self.assertEqual(response.status_code, 200)
        
        # Test IngestionJob add
        response = self.client.get(reverse('admin:recipe_ingestion_ingestionjob_add'))
        self.assertEqual(response.status_code, 200)
        
        # Test ExtractedRecipe add
        response = self.client.get(reverse('admin:recipe_ingestion_extractedrecipe_add'))
        self.assertEqual(response.status_code, 200)
        
        # Test ProcessingLog add
        response = self.client.get(reverse('admin:recipe_ingestion_processinglog_add'))
        self.assertEqual(response.status_code, 200)
        
        # Test IngredientMapping add
        response = self.client.get(reverse('admin:recipe_ingestion_ingredientmapping_add'))
        self.assertEqual(response.status_code, 200)
