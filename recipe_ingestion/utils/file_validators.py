"""
File validation utilities for recipe ingestion.

This module provides reusable file validation functions to eliminate
code duplication and ensure consistent validation across the system.
"""

import os
from typing import Optional, List, Tuple, Union
from django.core.files.uploadedfile import UploadedFile
from django.core.exceptions import ValidationError

from .constants import FileLimits, ContentTypes, ValidationMessages


class FileValidator:
    """Base file validator with common validation logic."""
    
    @staticmethod
    def validate_file_size(file: UploadedFile, max_size: int) -> Optional[str]:
        """
        Validate file size.
        
        Args:
            file: The uploaded file to validate
            max_size: Maximum allowed size in bytes
            
        Returns:
            Error message if validation fails, None if valid
        """
        if file.size > max_size:
            max_size_mb = max_size // (1024 * 1024)
            return ValidationMessages.FILE_TOO_LARGE.format(max_size=max_size_mb)
        return None
    
    @staticmethod
    def validate_file_type(file: UploadedFile, allowed_types: List[str]) -> Optional[str]:
        """
        Validate file content type.
        
        Args:
            file: The uploaded file to validate
            allowed_types: List of allowed MIME types
            
        Returns:
            Error message if validation fails, None if valid
        """
        if file.content_type not in allowed_types:
            supported_types = ", ".join(allowed_types)
            return ValidationMessages.UNSUPPORTED_FILE_TYPE.format(
                file_type=file.content_type,
                supported_types=supported_types
            )
        return None
    
    @staticmethod
    def validate_filename(filename: str) -> Optional[str]:
        """
        Validate filename.
        
        Args:
            filename: The filename to validate
            
        Returns:
            Error message if validation fails, None if valid
        """
        if not filename or len(filename) < FileLimits.MIN_FILENAME_LENGTH:
            return ValidationMessages.INVALID_FILENAME
        
        if len(filename) > FileLimits.MAX_FILENAME_LENGTH:
            return ValidationMessages.INVALID_FILENAME
        
        # Check for dangerous characters
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in filename for char in dangerous_chars):
            return ValidationMessages.INVALID_FILENAME
        
        return None
    
    @classmethod
    def validate_file(cls, file: UploadedFile, max_size: int, allowed_types: List[str]) -> Optional[str]:
        """
        Comprehensive file validation.
        
        Args:
            file: The uploaded file to validate
            max_size: Maximum allowed size in bytes
            allowed_types: List of allowed MIME types
            
        Returns:
            Error message if validation fails, None if valid
        """
        # Check if file is provided
        if not file:
            return ValidationMessages.FILE_NOT_PROVIDED
        
        # Validate filename
        filename_error = cls.validate_filename(file.name)
        if filename_error:
            return filename_error
        
        # Validate file size
        size_error = cls.validate_file_size(file, max_size)
        if size_error:
            return size_error
        
        # Validate file type
        type_error = cls.validate_file_type(file, allowed_types)
        if type_error:
            return type_error
        
        return None


class ImageFileValidator(FileValidator):
    """Specialized validator for image files."""
    
    @classmethod
    def validate_image_file(cls, file: UploadedFile, max_size: int = None) -> Optional[str]:
        """
        Validate an image file.
        
        Args:
            file: The uploaded image file to validate
            max_size: Maximum allowed size in bytes (defaults to FileLimits.MAX_IMAGE_SIZE)
            
        Returns:
            Error message if validation fails, None if valid
        """
        if max_size is None:
            max_size = FileLimits.MAX_IMAGE_SIZE
        
        return cls.validate_file(file, max_size, ContentTypes.IMAGE_TYPES)
    
    @classmethod
    def validate_image_files(cls, files: List[UploadedFile], max_total_size: int = None) -> Optional[str]:
        """
        Validate multiple image files.
        
        Args:
            files: List of uploaded image files to validate
            max_total_size: Maximum total size for all files (defaults to FileLimits.MAX_MULTI_IMAGE_SIZE)
            
        Returns:
            Error message if validation fails, None if valid
        """
        if not files:
            return ValidationMessages.FILE_NOT_PROVIDED
        
        if len(files) > FileLimits.MAX_IMAGE_COUNT:
            return f"Too many files. Maximum: {FileLimits.MAX_IMAGE_COUNT}"
        
        if max_total_size is None:
            max_total_size = FileLimits.MAX_MULTI_IMAGE_SIZE
        
        total_size = sum(file.size for file in files)
        if total_size > max_total_size:
            max_size_mb = max_total_size // (1024 * 1024)
            return ValidationMessages.FILE_TOO_LARGE.format(max_size=max_size_mb)
        
        # Validate each file individually
        for i, file in enumerate(files):
            error = cls.validate_image_file(file)
            if error:
                return f"File {i+1}: {error}"
        
        return None


class AttachmentFileValidator(FileValidator):
    """Specialized validator for email attachments."""
    
    @classmethod
    def validate_attachment_file(cls, file: UploadedFile) -> Optional[str]:
        """
        Validate an email attachment file.
        
        Args:
            file: The uploaded attachment file to validate
            
        Returns:
            Error message if validation fails, None if valid
        """
        return cls.validate_file(file, FileLimits.MAX_ATTACHMENT_SIZE, ContentTypes.ALL_SUPPORTED_TYPES)
    
    @classmethod
    def validate_attachment_files(cls, files: List[UploadedFile]) -> Optional[str]:
        """
        Validate multiple email attachment files.
        
        Args:
            files: List of uploaded attachment files to validate
            
        Returns:
            Error message if validation fails, None if valid
        """
        if not files:
            return ValidationMessages.FILE_NOT_PROVIDED
        
        if len(files) > FileLimits.MAX_IMAGE_COUNT:  # Reusing image count limit for attachments
            return f"Too many attachments. Maximum: {FileLimits.MAX_IMAGE_COUNT}"
        
        # Validate each file individually
        for i, file in enumerate(files):
            error = cls.validate_attachment_file(file)
            if error:
                return f"Attachment {i+1}: {error}"
        
        return None


class FileValidationResult:
    """Result object for file validation operations."""
    
    def __init__(self, is_valid: bool, error_message: Optional[str] = None):
        self.is_valid = is_valid
        self.error_message = error_message
    
    def __bool__(self) -> bool:
        return self.is_valid
    
    def __str__(self) -> str:
        return self.error_message or "Valid"


def validate_uploaded_file(file: UploadedFile, file_type: str = 'image', max_size: int = None) -> FileValidationResult:
    """
    Convenience function for file validation.
    
    Args:
        file: The uploaded file to validate
        file_type: Type of file ('image', 'attachment', 'document')
        max_size: Maximum allowed size in bytes
        
    Returns:
        FileValidationResult object
    """
    if file_type == 'image':
        error = ImageFileValidator.validate_image_file(file, max_size)
    elif file_type == 'attachment':
        error = AttachmentFileValidator.validate_attachment_file(file)
    else:
        error = FileValidator.validate_file(file, max_size or FileLimits.MAX_IMAGE_SIZE, ContentTypes.ALL_SUPPORTED_TYPES)
    
    return FileValidationResult(is_valid=error is None, error_message=error)


def validate_multiple_files(files: List[UploadedFile], file_type: str = 'image', max_total_size: int = None) -> FileValidationResult:
    """
    Convenience function for multiple file validation.
    
    Args:
        files: List of uploaded files to validate
        file_type: Type of files ('image', 'attachment')
        max_total_size: Maximum total size for all files
        
    Returns:
        FileValidationResult object
    """
    if file_type == 'image':
        error = ImageFileValidator.validate_image_files(files, max_total_size)
    elif file_type == 'attachment':
        error = AttachmentFileValidator.validate_attachment_files(files)
    else:
        error = "Unsupported file type for multiple file validation"
    
    return FileValidationResult(is_valid=error is None, error_message=error)
