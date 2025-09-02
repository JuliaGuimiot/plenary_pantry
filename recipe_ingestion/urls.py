from django.urls import path
from . import views

app_name = 'recipe_ingestion'

urlpatterns = [
    # Dashboard and main views
    path('', views.ingestion_dashboard, name='dashboard'),
    path('jobs/', views.job_list, name='job_list'),
    
    # Ingestion methods
    path('upload-image/', views.upload_image, name='upload_image'),
    path('mobile-upload/', views.mobile_upload, name='mobile_upload'),
    path('process-url/', views.process_url, name='process_url'),
    path('manual-input/', views.manual_input, name='manual_input'),
    
    # Job management
    path('job/<uuid:job_id>/', views.job_detail, name='job_detail'),
    path('job/<uuid:job_id>/normalize/', views.normalize_recipes, name='normalize_recipes'),
    path('job/<uuid:job_id>/delete/', views.delete_job, name='delete_job'),
    
    # Ingredient mappings
    path('mappings/', views.ingredient_mappings, name='ingredient_mappings'),
    path('mappings/<int:mapping_id>/edit/', views.edit_ingredient_mapping, name='edit_mapping'),
    
    # Email ingestion
    path('email-mappings/', views.email_mappings, name='email_mappings'),
    path('email-history/', views.email_ingestion_history, name='email_history'),
    
    # API endpoints
    path('api/process/', views.api_process_source, name='api_process_source'),
    path('api/job/<uuid:job_id>/status/', views.api_job_status, name='api_job_status'),
]
