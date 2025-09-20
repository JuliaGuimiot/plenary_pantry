"""
Recipe ingestion services package.

This package contains specialized services that follow the Single Responsibility Principle:
- OCRService: Handles image processing and text extraction
- WebScraperService: Handles URL content extraction and web scraping
- RecipeParserService: Handles recipe parsing from text
- RecipeNormalizerService: Handles recipe normalization and database operations
- RecipeIngestionService: Orchestrates all other services
"""

# Import services that don't require Django
from .ocr_service import OCRService
from .web_scraper_service import WebScraperService
from .recipe_parser_service import RecipeParserService

# Import Django-dependent services only when Django is available
try:
    from .ingredient_normalizer import IngredientNormalizer
    from .recipe_normalizer_service import RecipeNormalizerService
    from .recipe_ingestion_service import RecipeIngestionService
    _django_available = True
except ImportError:
    _django_available = False

__all__ = [
    'OCRService',
    'WebScraperService', 
    'RecipeParserService',
]

if _django_available:
    __all__.extend([
        'IngredientNormalizer',
        'RecipeNormalizerService',
        'RecipeIngestionService',
    ])
