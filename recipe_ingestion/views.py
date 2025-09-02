import json
import logging
from typing import Dict, Any
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal

from .models import (
    IngestionSource, IngestionJob, ExtractedRecipe, 
    IngredientMapping, ProcessingLog
)
from .services import RecipeIngestionService
from plenary_pantry.models import Recipe

logger = logging.getLogger(__name__)


@login_required
def ingestion_dashboard(request):
    """Main dashboard for recipe ingestion"""
    # Get user's recent ingestion sources
    recent_sources = IngestionSource.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    # Get recent jobs
    recent_jobs = IngestionJob.objects.filter(
        source__user=request.user
    ).order_by('-started_at')[:10]
    
    # Get statistics
    total_sources = IngestionSource.objects.filter(user=request.user).count()
    total_jobs = IngestionJob.objects.filter(source__user=request.user).count()
    successful_jobs = IngestionJob.objects.filter(
        source__user=request.user, 
        status='completed'
    ).count()
    
    context = {
        'recent_sources': recent_sources,
        'recent_jobs': recent_jobs,
        'total_sources': total_sources,
        'total_jobs': total_jobs,
        'successful_jobs': successful_jobs,
        'success_rate': (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
    }
    
    return render(request, 'recipe_ingestion/dashboard.html', context)


@login_required
def upload_image(request):
    """Upload and process recipe images"""
    if request.method == 'POST':
        try:
            # Get uploaded file
            uploaded_file = request.FILES.get('recipe_image')
            if not uploaded_file:
                messages.error(request, 'Please select an image file.')
                return redirect('ingestion_dashboard')
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if uploaded_file.content_type not in allowed_types:
                messages.error(request, 'Please upload a valid image file (JPEG, PNG, GIF).')
                return redirect('ingestion_dashboard')
            
            # Create ingestion source
            source = IngestionSource.objects.create(
                user=request.user,
                source_type='image',
                source_name=uploaded_file.name,
                source_file=uploaded_file
            )
            
            # Process the source
            service = RecipeIngestionService(request.user)
            job = service.process_source(source)
            
            messages.success(request, f'Image uploaded successfully! Processing job created: {job.id}')
            return redirect('job_detail', job_id=job.id)
            
        except Exception as e:
            logger.error(f"Image upload failed: {str(e)}")
            messages.error(request, f'Failed to process image: {str(e)}')
            return redirect('ingestion_dashboard')
    
    return render(request, 'recipe_ingestion/upload_image.html')


@login_required
def process_url(request):
    """Process recipe from URL"""
    if request.method == 'POST':
        try:
            url = request.POST.get('recipe_url', '').strip()
            if not url:
                messages.error(request, 'Please provide a valid URL.')
                return redirect('ingestion_dashboard')
            
            # Validate URL format
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Create ingestion source
            source = IngestionSource.objects.create(
                user=request.user,
                source_type='url',
                source_name=f'Recipe from {url}',
                source_url=url
            )
            
            # Process the source
            service = RecipeIngestionService(request.user)
            job = service.process_source(source)
            
            messages.success(request, f'URL processed successfully! Processing job created: {job.id}')
            return redirect('job_detail', job_id=job.id)
            
        except Exception as e:
            logger.error(f"URL processing failed: {str(e)}")
            messages.error(request, f'Failed to process URL: {str(e)}')
            return redirect('ingestion_dashboard')
    
    return render(request, 'recipe_ingestion/process_url.html')


@login_required
def manual_input(request):
    """Manual recipe text input"""
    if request.method == 'POST':
        try:
            recipe_text = request.POST.get('recipe_text', '').strip()
            recipe_name = request.POST.get('recipe_name', 'Manual Recipe').strip()
            
            if not recipe_text:
                messages.error(request, 'Please provide recipe text.')
                return redirect('ingestion_dashboard')
            
            # Create ingestion source
            source = IngestionSource.objects.create(
                user=request.user,
                source_type='text',
                source_name=recipe_name,
                raw_text=recipe_text
            )
            
            # Process the source
            service = RecipeIngestionService(request.user)
            job = service.process_source(source)
            
            messages.success(request, f'Recipe text processed successfully! Processing job created: {job.id}')
            return redirect('job_detail', job_id=job.id)
            
        except Exception as e:
            logger.error(f"Manual input processing failed: {str(e)}")
            messages.error(request, f'Failed to process recipe text: {str(e)}')
            return redirect('ingestion_dashboard')
    
    return render(request, 'recipe_ingestion/manual_input.html')


@login_required
def job_list(request):
    """List all ingestion jobs for the user"""
    jobs = IngestionJob.objects.filter(
        source__user=request.user
    ).order_by('-started_at')
    
    # Pagination
    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'jobs': page_obj.object_list
    }
    
    return render(request, 'recipe_ingestion/job_list.html', context)


@login_required
def job_detail(request, job_id):
    """View details of a specific ingestion job"""
    job = get_object_or_404(IngestionJob, id=job_id, source__user=request.user)
    
    # Get extracted recipes
    extracted_recipes = job.extracted_recipes.all()
    
    # Get processing logs
    logs = job.logs.all().order_by('created_at')
    
    context = {
        'job': job,
        'extracted_recipes': extracted_recipes,
        'logs': logs
    }
    
    return render(request, 'recipe_ingestion/job_detail.html', context)


@login_required
def normalize_recipes(request, job_id):
    """Normalize and save extracted recipes"""
    job = get_object_or_404(IngestionJob, id=job_id, source__user=request.user)
    
    if request.method == 'POST':
        try:
            # Get selected recipes to normalize
            selected_recipes = request.POST.getlist('selected_recipes')
            
            if not selected_recipes:
                messages.error(request, 'Please select at least one recipe to normalize.')
                return redirect('job_detail', job_id=job_id)
            
            # Filter extracted recipes
            extracted_recipes = job.extracted_recipes.filter(id__in=selected_recipes)
            
            # Normalize and save recipes
            service = RecipeIngestionService(request.user)
            saved_recipes = service.normalize_and_save_recipes(job)
            
            messages.success(request, f'Successfully saved {len(saved_recipes)} recipes!')
            return redirect('job_detail', job_id=job_id)
            
        except Exception as e:
            logger.error(f"Recipe normalization failed: {str(e)}")
            messages.error(request, f'Failed to normalize recipes: {str(e)}')
            return redirect('job_detail', job_id=job_id)
    
    # Get extracted recipes for selection
    extracted_recipes = job.extracted_recipes.all()
    
    context = {
        'job': job,
        'extracted_recipes': extracted_recipes
    }
    
    return render(request, 'recipe_ingestion/normalize_recipes.html', context)


@login_required
def ingredient_mappings(request):
    """Manage ingredient mappings"""
    mappings = IngredientMapping.objects.all().order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        mappings = mappings.filter(
            Q(raw_text__icontains=search_query) |
            Q(normalized_ingredient__name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(mappings, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'mappings': page_obj.object_list,
        'search_query': search_query
    }
    
    return render(request, 'recipe_ingestion/ingredient_mappings.html', context)


@login_required
def edit_ingredient_mapping(request, mapping_id):
    """Edit ingredient mapping"""
    mapping = get_object_or_404(IngredientMapping, id=mapping_id)
    
    if request.method == 'POST':
        try:
            # Update mapping
            ingredient_id = request.POST.get('ingredient_id')
            quantity = request.POST.get('quantity')
            unit_id = request.POST.get('unit_id')
            preparation_method = request.POST.get('preparation_method', '')
            
            if ingredient_id:
                from plenary_pantry.models import Ingredient, Unit
                ingredient = get_object_or_404(Ingredient, id=ingredient_id)
                mapping.normalized_ingredient = ingredient
            
            if quantity:
                mapping.quantity = Decimal(quantity)
            
            if unit_id:
                unit = get_object_or_404(Unit, id=unit_id)
                mapping.unit = unit
            
            mapping.preparation_method = preparation_method
            mapping.save()
            
            messages.success(request, 'Ingredient mapping updated successfully!')
            return redirect('ingredient_mappings')
            
        except Exception as e:
            messages.error(request, f'Failed to update mapping: {str(e)}')
    
    # Get available ingredients and units for dropdown
    from plenary_pantry.models import Ingredient, Unit
    ingredients = Ingredient.objects.all().order_by('name')
    units = Unit.objects.all().order_by('name')
    
    context = {
        'mapping': mapping,
        'ingredients': ingredients,
        'units': units
    }
    
    return render(request, 'recipe_ingestion/edit_mapping.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def api_process_source(request):
    """API endpoint for processing recipe sources"""
    try:
        # Handle multipart form data for image uploads
        if request.content_type and 'multipart/form-data' in request.content_type:
            return _handle_multipart_upload(request)
        
        # Handle JSON data for other sources
        data = json.loads(request.body)
        source_type = data.get('source_type')
        user_id = data.get('user_id')
        auto_normalize = data.get('auto_normalize', True)  # Default to True
        
        if not source_type or not user_id:
            return JsonResponse({
                'error': 'Missing required fields: source_type, user_id'
            }, status=400)
        
        # Create source based on type
        if source_type == 'url':
            source = IngestionSource.objects.create(
                user_id=user_id,
                source_type='url',
                source_name=data.get('source_name', 'API Import'),
                source_url=data.get('source_url')
            )
        elif source_type == 'text':
            source = IngestionSource.objects.create(
                user_id=user_id,
                source_type='text',
                source_name=data.get('source_name', 'API Import'),
                raw_text=data.get('raw_text')
            )
        elif source_type == 'image':
            return JsonResponse({
                'error': 'Use multipart/form-data for image uploads'
            }, status=400)
        else:
            return JsonResponse({
                'error': f'Unsupported source type: {source_type}'
            }, status=400)
        
        # Process the source
        service = RecipeIngestionService(source.user)
        job = service.process_source(source)
        
        # Auto-normalize if requested
        saved_recipes = []
        if auto_normalize and job.extracted_recipes.exists():
            try:
                saved_recipes = service.normalize_and_save_recipes(job)
            except Exception as e:
                logger.error(f"Auto-normalization failed: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'job_id': str(job.id),
            'status': job.status,
            'recipes_found': job.extracted_recipes.count(),
            'recipes_saved': len(saved_recipes),
            'auto_normalized': auto_normalize
        })
        
    except Exception as e:
        logger.error(f"API processing failed: {str(e)}")
        return JsonResponse({
            'error': str(e)
        }, status=500)


def _handle_multipart_upload(request):
    """Handle multipart form data for image uploads"""
    try:
        user_id = request.POST.get('user_id')
        auto_normalize = request.POST.get('auto_normalize', 'true').lower() == 'true'
        source_name = request.POST.get('source_name', 'Mobile Photo Upload')
        upload_type = request.POST.get('upload_type', 'single')  # 'single' or 'multi'
        
        if not user_id:
            return JsonResponse({
                'error': 'Missing required field: user_id'
            }, status=400)
        
        # Handle multi-image upload
        if upload_type == 'multi':
            return _handle_multi_image_upload(request, user_id, auto_normalize, source_name)
        
        # Handle single image upload
        if 'image' not in request.FILES:
            return JsonResponse({
                'error': 'No image file provided'
            }, status=400)
        
        image_file = request.FILES['image']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/heic', 'image/heif']
        if image_file.content_type not in allowed_types:
            return JsonResponse({
                'error': f'Unsupported file type: {image_file.content_type}. Supported: {", ".join(allowed_types)}'
            }, status=400)
        
        # Validate file size (max 10MB)
        if image_file.size > 10 * 1024 * 1024:
            return JsonResponse({
                'error': 'File too large. Maximum size: 10MB'
            }, status=400)
        
        # Create source with image file
        source = IngestionSource.objects.create(
            user_id=user_id,
            source_type='image',
            source_name=source_name,
            source_file=image_file
        )
        
        # Process the source
        service = RecipeIngestionService(source.user)
        job = service.process_source(source)
        
        # Auto-normalize if requested
        saved_recipes = []
        if auto_normalize and job.extracted_recipes.exists():
            try:
                saved_recipes = service.normalize_and_save_recipes(job)
            except Exception as e:
                logger.error(f"Auto-normalization failed: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'job_id': str(job.id),
            'status': job.status,
            'recipes_found': job.extracted_recipes.count(),
            'recipes_saved': len(saved_recipes),
            'auto_normalized': auto_normalize,
            'file_name': image_file.name,
            'file_size': image_file.size
        })
        
    except Exception as e:
        logger.error(f"Multipart upload processing failed: {str(e)}")
        return JsonResponse({
            'error': str(e)
        }, status=500)


def _handle_multi_image_upload(request, user_id, auto_normalize, source_name):
    """Handle multi-image upload for recipe pages"""
    try:
        # Get all image files
        image_files = request.FILES.getlist('images')
        
        if not image_files:
            return JsonResponse({
                'error': 'No image files provided'
            }, status=400)
        
        # Validate number of images (max 10 pages)
        if len(image_files) > 10:
            return JsonResponse({
                'error': 'Too many images. Maximum: 10 pages'
            }, status=400)
        
        # Validate each file
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/heic', 'image/heif']
        total_size = 0
        
        for i, image_file in enumerate(image_files):
            if image_file.content_type not in allowed_types:
                return JsonResponse({
                    'error': f'Unsupported file type in image {i+1}: {image_file.content_type}'
                }, status=400)
            
            if image_file.size > 10 * 1024 * 1024:
                return JsonResponse({
                    'error': f'Image {i+1} too large. Maximum size: 10MB'
                }, status=400)
            
            total_size += image_file.size
        
        # Check total size (max 50MB for multi-image)
        if total_size > 50 * 1024 * 1024:
            return JsonResponse({
                'error': 'Total file size too large. Maximum: 50MB'
            }, status=400)
        
        # Create multi-image source
        source = IngestionSource.objects.create(
            user_id=user_id,
            source_type='multi_image',
            source_name=source_name
        )
        
        # Create multi-image records
        for i, image_file in enumerate(image_files):
            page_number = i + 1
            page_type = request.POST.get(f'page_type_{i}', 'unknown')
            
            from .models import MultiImageSource
            MultiImageSource.objects.create(
                source=source,
                image_file=image_file,
                page_number=page_number,
                page_type=page_type
            )
        
        # Process the source
        service = RecipeIngestionService(source.user)
        job = service.process_source(source)
        
        # Auto-normalize if requested
        saved_recipes = []
        if auto_normalize and job.extracted_recipes.exists():
            try:
                saved_recipes = service.normalize_and_save_recipes(job)
            except Exception as e:
                logger.error(f"Auto-normalization failed: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'job_id': str(job.id),
            'status': job.status,
            'recipes_found': job.extracted_recipes.count(),
            'recipes_saved': len(saved_recipes),
            'auto_normalized': auto_normalize,
            'images_count': len(image_files),
            'total_size': total_size
        })
        
    except Exception as e:
        logger.error(f"Multi-image upload processing failed: {str(e)}")
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
def api_job_status(request, job_id):
    """API endpoint to check job status"""
    try:
        job = get_object_or_404(IngestionJob, id=job_id, source__user=request.user)
        
        return JsonResponse({
            'job_id': str(job.id),
            'status': job.status,
            'recipes_found': job.recipes_found,
            'recipes_processed': job.recipes_processed,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'error_message': job.error_message
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
def mobile_upload(request):
    """Mobile-friendly recipe photo upload interface"""
    return render(request, 'recipe_ingestion/mobile_upload.html')


@login_required
def delete_job(request, job_id):
    """Delete an ingestion job"""
    job = get_object_or_404(IngestionJob, id=job_id, source__user=request.user)
    
    if request.method == 'POST':
        try:
            # Delete associated files
            if job.source.source_file:
                job.source.source_file.delete(save=False)
            
            # Delete the job and source
            job.source.delete()
            
            messages.success(request, 'Job deleted successfully!')
            return redirect('job_list')
            
        except Exception as e:
            messages.error(request, f'Failed to delete job: {str(e)}')
    
    context = {
        'job': job
    }
    
    return render(request, 'recipe_ingestion/delete_job.html', context)


@login_required
def email_mappings(request):
    """Manage user email mappings"""
    from .models import UserEmailMapping
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            email_address = request.POST.get('email_address')
            if email_address:
                try:
                    UserEmailMapping.objects.create(
                        user=request.user,
                        email_address=email_address
                    )
                    messages.success(request, f'Email mapping added: {email_address}')
                except Exception as e:
                    messages.error(request, f'Error adding email mapping: {str(e)}')
        
        elif action == 'toggle':
            mapping_id = request.POST.get('mapping_id')
            try:
                mapping = UserEmailMapping.objects.get(id=mapping_id, user=request.user)
                mapping.is_active = not mapping.is_active
                mapping.save()
                status = 'activated' if mapping.is_active else 'deactivated'
                messages.success(request, f'Email mapping {status}: {mapping.email_address}')
            except UserEmailMapping.DoesNotExist:
                messages.error(request, 'Email mapping not found')
        
        elif action == 'delete':
            mapping_id = request.POST.get('mapping_id')
            try:
                mapping = UserEmailMapping.objects.get(id=mapping_id, user=request.user)
                email_address = mapping.email_address
                mapping.delete()
                messages.success(request, f'Email mapping deleted: {email_address}')
            except UserEmailMapping.DoesNotExist:
                messages.error(request, 'Email mapping not found')
        
        return redirect('email_mappings')
    
    # Get user's email mappings
    mappings = UserEmailMapping.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'mappings': mappings,
    }
    
    return render(request, 'recipe_ingestion/email_mappings.html', context)


@login_required
def email_ingestion_history(request):
    """View email ingestion history"""
    from .models import EmailIngestionSource
    from django.core.paginator import Paginator
    
    # Get email sources for the user
    email_sources = EmailIngestionSource.objects.filter(
        source__user=request.user
    ).select_related('source').prefetch_related('attachments').order_by('-received_at')
    
    # Pagination
    paginator = Paginator(email_sources, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'email_sources': page_obj,
    }
    
    return render(request, 'recipe_ingestion/email_history.html', context)
