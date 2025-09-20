"""
Constants used throughout the recipe ingestion system.

This module centralizes all magic numbers, repeated strings, and configuration
values to improve maintainability and reduce duplication.
"""

from typing import List


class FileLimits:
    """File size and count limits for different upload types."""
    
    # Image file limits
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_MULTI_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB for multi-image uploads
    MAX_IMAGE_COUNT = 10  # Maximum number of images in multi-image upload
    
    # Email attachment limits
    MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10MB per attachment
    
    # General file limits
    MAX_FILENAME_LENGTH = 500
    MIN_FILENAME_LENGTH = 1


class ContentTypes:
    """Supported content types for different file categories."""
    
    # Image content types
    IMAGE_TYPES: List[str] = [
        'image/jpeg',
        'image/jpg', 
        'image/png',
        'image/gif',
        'image/heic',
        'image/heif'
    ]
    
    # Document content types
    DOCUMENT_TYPES: List[str] = [
        'application/pdf',
        'text/plain',
        'text/html'
    ]
    
    # All supported types
    ALL_SUPPORTED_TYPES: List[str] = IMAGE_TYPES + DOCUMENT_TYPES


class WebScrapingConfig:
    """Configuration for web scraping operations."""
    
    # User agent for web requests
    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    )
    
    # Request timeouts
    REQUEST_TIMEOUT = 10  # seconds
    SELENIUM_TIMEOUT = 10  # seconds
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds


class RecipeProcessingConfig:
    """Configuration for recipe processing operations."""
    
    # OCR configuration
    OCR_CONFIDENCE_THRESHOLD = 0.5
    
    # Recipe parsing thresholds
    MIN_INGREDIENT_LENGTH = 3
    MIN_INSTRUCTION_LENGTH = 10
    MIN_RECIPE_NAME_LENGTH = 2
    
    # Duplicate detection
    SIMILARITY_THRESHOLD = 0.8


class EmailConfig:
    """Configuration for email processing."""
    
    # Email processing limits
    MAX_EMAIL_SIZE = 25 * 1024 * 1024  # 25MB
    MAX_ATTACHMENTS_PER_EMAIL = 20
    
    # Content extraction
    MAX_EMAIL_CONTENT_LENGTH = 1000000  # 1MB of text content


class APIConfig:
    """Configuration for API endpoints."""
    
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = 100  # requests per hour
    RATE_LIMIT_WINDOW = 3600  # seconds
    
    # Response limits
    MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB


class ValidationMessages:
    """Standard validation error messages."""
    
    # File validation messages
    FILE_TOO_LARGE = "File too large. Maximum size: {max_size}MB"
    UNSUPPORTED_FILE_TYPE = "Unsupported file type: {file_type}. Supported: {supported_types}"
    FILE_NOT_PROVIDED = "No file provided"
    INVALID_FILENAME = "Invalid filename"
    
    # General validation messages
    MISSING_REQUIRED_FIELD = "Missing required field: {field_name}"
    INVALID_VALUE = "Invalid value for {field_name}: {value}"
    NOT_FOUND = "{resource} not found"
    ALREADY_EXISTS = "{resource} already exists"
    
    # Processing messages
    PROCESSING_FAILED = "Processing failed: {error_message}"
    UPLOAD_FAILED = "Upload failed: {error_message}"
    VALIDATION_FAILED = "Validation failed: {error_message}"


class StatusMessages:
    """Standard status messages for operations."""
    
    # Success messages
    UPLOAD_SUCCESS = "File uploaded successfully"
    PROCESSING_SUCCESS = "Processing completed successfully"
    RECIPE_SAVED = "Recipe saved successfully"
    
    # Info messages
    PROCESSING_STARTED = "Processing started"
    VALIDATION_PASSED = "Validation passed"
    
    # Warning messages
    PARTIAL_SUCCESS = "Operation completed with warnings"
    DUPLICATE_FOUND = "Duplicate found and handled"
