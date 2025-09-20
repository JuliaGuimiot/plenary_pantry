"""
Response helper utilities for consistent API responses.

This module provides standardized response creation functions to ensure
consistent API responses across the recipe ingestion system.
"""

from typing import Any, Dict, Optional, Union
from django.http import JsonResponse
from django.core.paginator import Paginator

from .constants import ValidationMessages, StatusMessages


class APIResponse:
    """Base class for API response creation."""
    
    @staticmethod
    def success(data: Dict[str, Any] = None, message: str = None, status: int = 200) -> JsonResponse:
        """
        Create a successful API response.
        
        Args:
            data: Response data dictionary
            message: Success message
            status: HTTP status code
            
        Returns:
            JsonResponse with success format
        """
        response_data = {'success': True}
        
        if data:
            response_data.update(data)
        
        if message:
            response_data['message'] = message
        
        return JsonResponse(response_data, status=status)
    
    @staticmethod
    def error(message: str, status: int = 400, error_code: str = None, details: Dict[str, Any] = None) -> JsonResponse:
        """
        Create an error API response.
        
        Args:
            message: Error message
            status: HTTP status code
            error_code: Optional error code for client handling
            details: Additional error details
            
        Returns:
            JsonResponse with error format
        """
        response_data = {
            'success': False,
            'error': message
        }
        
        if error_code:
            response_data['error_code'] = error_code
        
        if details:
            response_data['details'] = details
        
        return JsonResponse(response_data, status=status)
    
    @staticmethod
    def validation_error(message: str, field: str = None, details: Dict[str, Any] = None) -> JsonResponse:
        """
        Create a validation error response.
        
        Args:
            message: Validation error message
            field: Field that failed validation
            details: Additional validation details
            
        Returns:
            JsonResponse with validation error format
        """
        response_data = {
            'success': False,
            'error': message,
            'error_type': 'validation_error'
        }
        
        if field:
            response_data['field'] = field
        
        if details:
            response_data['details'] = details
        
        return JsonResponse(response_data, status=400)
    
    @staticmethod
    def not_found(resource: str, identifier: str = None) -> JsonResponse:
        """
        Create a not found error response.
        
        Args:
            resource: Type of resource not found
            identifier: Specific identifier that wasn't found
            
        Returns:
            JsonResponse with not found error format
        """
        message = ValidationMessages.NOT_FOUND.format(resource=resource)
        if identifier:
            message += f": {identifier}"
        
        return APIResponse.error(message, status=404, error_code='NOT_FOUND')
    
    @staticmethod
    def already_exists(resource: str, identifier: str = None) -> JsonResponse:
        """
        Create an already exists error response.
        
        Args:
            resource: Type of resource that already exists
            identifier: Specific identifier that already exists
            
        Returns:
            JsonResponse with already exists error format
        """
        message = ValidationMessages.ALREADY_EXISTS.format(resource=resource)
        if identifier:
            message += f": {identifier}"
        
        return APIResponse.error(message, status=409, error_code='ALREADY_EXISTS')


class ErrorResponse:
    """Specialized error response creator."""
    
    @staticmethod
    def missing_field(field_name: str) -> JsonResponse:
        """Create missing required field error."""
        message = ValidationMessages.MISSING_REQUIRED_FIELD.format(field_name=field_name)
        return APIResponse.error(message, status=400, error_code='MISSING_FIELD')
    
    @staticmethod
    def invalid_value(field_name: str, value: Any) -> JsonResponse:
        """Create invalid value error."""
        message = ValidationMessages.INVALID_VALUE.format(field_name=field_name, value=value)
        return APIResponse.error(message, status=400, error_code='INVALID_VALUE')
    
    @staticmethod
    def file_validation_error(error_message: str) -> JsonResponse:
        """Create file validation error."""
        return APIResponse.error(error_message, status=400, error_code='FILE_VALIDATION_ERROR')
    
    @staticmethod
    def processing_error(error_message: str, details: Dict[str, Any] = None) -> JsonResponse:
        """Create processing error."""
        message = ValidationMessages.PROCESSING_FAILED.format(error_message=error_message)
        return APIResponse.error(message, status=500, error_code='PROCESSING_ERROR', details=details)
    
    @staticmethod
    def upload_error(error_message: str, details: Dict[str, Any] = None) -> JsonResponse:
        """Create upload error."""
        message = ValidationMessages.UPLOAD_FAILED.format(error_message=error_message)
        return APIResponse.error(message, status=500, error_code='UPLOAD_ERROR', details=details)


class SuccessResponse:
    """Specialized success response creator."""
    
    @staticmethod
    def upload_success(file_name: str, file_size: int = None, job_id: str = None) -> JsonResponse:
        """Create upload success response."""
        data = {
            'file_name': file_name,
            'message': StatusMessages.UPLOAD_SUCCESS
        }
        
        if file_size is not None:
            data['file_size'] = file_size
        
        if job_id:
            data['job_id'] = job_id
        
        return APIResponse.success(data)
    
    @staticmethod
    def processing_success(job_id: str, recipes_found: int = None, recipes_saved: int = None) -> JsonResponse:
        """Create processing success response."""
        data = {
            'job_id': job_id,
            'message': StatusMessages.PROCESSING_SUCCESS
        }
        
        if recipes_found is not None:
            data['recipes_found'] = recipes_found
        
        if recipes_saved is not None:
            data['recipes_saved'] = recipes_saved
        
        return APIResponse.success(data)
    
    @staticmethod
    def recipe_saved(recipe_id: str, recipe_name: str = None) -> JsonResponse:
        """Create recipe saved success response."""
        data = {
            'recipe_id': recipe_id,
            'message': StatusMessages.RECIPE_SAVED
        }
        
        if recipe_name:
            data['recipe_name'] = recipe_name
        
        return APIResponse.success(data)
    
    @staticmethod
    def paired_photo_upload_success(photo_type: str, is_complete: bool, job_id: str = None) -> JsonResponse:
        """Create paired photo upload success response."""
        data = {
            'photo_type': photo_type,
            'is_complete': is_complete,
            'auto_process': is_complete,
            'message': StatusMessages.UPLOAD_SUCCESS
        }
        
        if job_id:
            data['job_id'] = job_id
        
        return APIResponse.success(data)


class PaginatedResponse:
    """Helper for creating paginated responses."""
    
    @staticmethod
    def create(queryset, page_number: int, page_size: int = 20, serializer_func=None) -> Dict[str, Any]:
        """
        Create paginated response data.
        
        Args:
            queryset: Django queryset to paginate
            page_number: Current page number
            page_size: Number of items per page
            serializer_func: Optional function to serialize each item
            
        Returns:
            Dictionary with pagination data
        """
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page_number)
        
        items = page_obj.object_list
        if serializer_func:
            items = [serializer_func(item) for item in items]
        
        return {
            'items': items,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'page_size': page_size
            }
        }


def create_api_response(success: bool, data: Dict[str, Any] = None, message: str = None, 
                       error: str = None, status: int = None) -> JsonResponse:
    """
    Convenience function for creating API responses.
    
    Args:
        success: Whether the operation was successful
        data: Response data dictionary
        message: Success or error message
        error: Error message (overrides message if success=False)
        status: HTTP status code
        
    Returns:
        JsonResponse
    """
    if success:
        return APIResponse.success(data, message, status or 200)
    else:
        return APIResponse.error(error or message or "Unknown error", status or 400)


def handle_validation_error(validation_result) -> JsonResponse:
    """
    Handle file validation result and return appropriate response.
    
    Args:
        validation_result: FileValidationResult object
        
    Returns:
        JsonResponse
    """
    if validation_result.is_valid:
        return APIResponse.success()
    else:
        return ErrorResponse.file_validation_error(str(validation_result))
