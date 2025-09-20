# Legacy services.py - This file is deprecated
# Use the new service classes in the services/ package instead

import logging
from .services import RecipeIngestionService

logger = logging.getLogger(__name__)

# For backward compatibility, export the main service
__all__ = ['RecipeIngestionService']