"""
Main Recipe Ingestion Service for orchestrating recipe processing.

This service coordinates all other services to handle the complete recipe
ingestion workflow from source processing to recipe creation.
"""

import logging
from typing import List
from datetime import datetime

from django.contrib.auth.models import User

from ..models import (
    IngestionSource, IngestionJob, ExtractedRecipe, 
    PairedPhotoSource, PairedPhotoJob, ProcessingLog
)
from .ocr_service import OCRService
from .web_scraper_service import WebScraperService
from .recipe_parser_service import RecipeParserService
from .recipe_normalizer_service import RecipeNormalizerService

logger = logging.getLogger(__name__)


class RecipeIngestionService:
    """Main service for orchestrating recipe ingestion and processing."""
    
    def __init__(self, user: User):
        """
        Initialize the recipe ingestion service.
        
        Args:
            user: User who owns the recipes
        """
        self.user = user
        self.ocr_service = OCRService()
        self.web_scraper_service = WebScraperService()
        self.recipe_parser = RecipeParserService()
        self.recipe_normalizer = RecipeNormalizerService(user)
    
    def process_source(self, source: IngestionSource) -> IngestionJob:
        """
        Process a recipe source and create a job.
        
        Args:
            source: Ingestion source to process
            
        Returns:
            Created ingestion job
        """
        job = IngestionJob.objects.create(source=source)
        
        try:
            self._log(job, "Starting processing", "info")
            
            if source.source_type == 'image':
                self._process_image_source(job, source)
            elif source.source_type == 'multi_image':
                self._process_multi_image_source(job, source)
            elif source.source_type == 'url':
                self._process_url_source(job, source)
            elif source.source_type == 'text':
                self._process_text_source(job, source)
            elif source.source_type == 'email':
                self._process_email_source(job, source)
            else:
                raise ValueError(f"Unsupported source type: {source.source_type}")
            
            job.status = 'completed'
            job.completed_at = datetime.now()
            job.save()
            
            self._log(job, "Processing completed successfully", "info")
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            self._log(job, f"Processing failed: {str(e)}", "error")
            logger.error(f"Recipe ingestion failed: {str(e)}", exc_info=True)
        
        return job
    
    def process_paired_photos(self, paired_source: PairedPhotoSource) -> PairedPhotoJob:
        """
        Process paired photos for ingredients and directions.
        
        Args:
            paired_source: Paired photo source to process
            
        Returns:
            Created paired photo job
        """
        job = PairedPhotoJob.objects.create(paired_source=paired_source)
        
        try:
            self._log_paired(job, "Starting paired photo processing", "info")
            
            # Update status to processing
            paired_source.status = 'processing'
            paired_source.save()
            
            # Process ingredients photo
            if paired_source.ingredients_photo:
                self._log_paired(job, "Processing ingredients photo", "info")
                ingredients_text = self.ocr_service.extract_text_from_image(paired_source.ingredients_photo.path)
                paired_source.ingredients_text = ingredients_text
                self._log_paired(job, f"Extracted {len(ingredients_text)} characters from ingredients photo", "info")
            
            # Process directions photo
            if paired_source.directions_photo:
                self._log_paired(job, "Processing directions photo", "info")
                directions_text = self.ocr_service.extract_text_from_image(paired_source.directions_photo.path)
                paired_source.directions_text = directions_text
                self._log_paired(job, f"Extracted {len(directions_text)} characters from directions photo", "info")
            
            # Combine the text
            combined_text = self._combine_paired_text(paired_source.ingredients_text, paired_source.directions_text)
            paired_source.combined_text = combined_text
            
            # Update processed timestamp
            paired_source.processed_at = datetime.now()
            paired_source.status = 'completed'
            paired_source.save()
            
            # Parse recipes from combined text
            recipes = self.recipe_parser.parse_recipes_from_text(combined_text)
            
            # Create extracted recipe records
            for recipe_data in recipes:
                ExtractedRecipe.objects.create(
                    job=job,
                    raw_name=recipe_data.get('name', paired_source.recipe_name or 'Untitled Recipe'),
                    raw_instructions=recipe_data.get('instructions', ''),
                    raw_ingredients=recipe_data.get('ingredients', []),
                    raw_metadata=recipe_data.get('metadata', {}),
                    confidence_score=recipe_data.get('confidence', 0.0)
                )
            
            job.recipes_found = len(recipes)
            job.recipes_processed = len(recipes)
            job.status = 'completed'
            job.completed_at = datetime.now()
            job.save()
            
            self._log_paired(job, f"Successfully processed paired photos: {len(recipes)} recipes found", "info")
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            paired_source.status = 'failed'
            paired_source.save()
            self._log_paired(job, f"Paired photo processing failed: {str(e)}", "error")
            logger.error(f"Paired photo processing failed: {str(e)}", exc_info=True)
        
        return job
    
    def normalize_and_save_recipes(self, job: IngestionJob) -> List:
        """
        Normalize and save recipes from an ingestion job.
        
        Args:
            job: Ingestion job containing extracted recipes
            
        Returns:
            List of saved Recipe objects
        """
        return self.recipe_normalizer.normalize_and_save_recipes(job)
    
    def _process_image_source(self, job: IngestionJob, source: IngestionSource):
        """Process image sources using OCR."""
        self._log(job, "Processing image with OCR", "info")
        
        # Extract text using OCR
        image_path = source.source_file.path
        extracted_text = self.ocr_service.extract_text_from_image(image_path)
        
        # Update source with extracted text
        source.raw_text = extracted_text
        source.processed_at = datetime.now()
        source.save()
        
        # Parse recipes from extracted text
        recipes = self.recipe_parser.parse_recipes_from_text(extracted_text)
        
        # Create extracted recipe records
        for recipe_data in recipes:
            ExtractedRecipe.objects.create(
                job=job,
                raw_name=recipe_data.get('name', 'Untitled Recipe'),
                raw_instructions=recipe_data.get('instructions', ''),
                raw_ingredients=recipe_data.get('ingredients', []),
                raw_metadata=recipe_data.get('metadata', {}),
                confidence_score=recipe_data.get('confidence', 0.0)
            )
        
        job.recipes_found = len(recipes)
        job.recipes_processed = len(recipes)
        job.save()
        
        self._log(job, f"Extracted {len(recipes)} recipes from image", "info")
    
    def _process_multi_image_source(self, job: IngestionJob, source: IngestionSource):
        """Process multi-image sources."""
        self._log(job, "Processing multi-image source", "info")
        
        # Get all image files
        image_files = source.multiimagesource_set.all().order_by('page_number')
        image_paths = [img.image_file.path for img in image_files]
        
        if not image_paths:
            self._log(job, "No images found in multi-image source", "warning")
            return
        
        # Extract text from all images
        extracted_text = self.ocr_service.extract_text_from_multiple_images(image_paths)
        
        # Clean up the text for better parsing
        cleaned_text = self.ocr_service.clean_multi_image_text(extracted_text)
        
        # Update source with extracted text
        source.raw_text = cleaned_text
        source.processed_at = datetime.now()
        source.save()
        
        # Parse recipes from extracted text
        recipes = self.recipe_parser.parse_recipes_from_text(cleaned_text)
        
        # Create extracted recipe records
        for recipe_data in recipes:
            ExtractedRecipe.objects.create(
                job=job,
                raw_name=recipe_data.get('name', 'Untitled Recipe'),
                raw_instructions=recipe_data.get('instructions', ''),
                raw_ingredients=recipe_data.get('ingredients', []),
                raw_metadata=recipe_data.get('metadata', {}),
                confidence_score=recipe_data.get('confidence', 0.0)
            )
        
        job.recipes_found = len(recipes)
        job.recipes_processed = len(recipes)
        job.save()
        
        self._log(job, f"Extracted {len(recipes)} recipes from {len(image_paths)} images", "info")
    
    def _process_url_source(self, job: IngestionJob, source: IngestionSource):
        """Process web URL sources."""
        self._log(job, "Processing URL source", "info")
        
        if not source.source_url:
            raise ValueError("No URL provided for URL source")
        
        # Extract content from URL
        extracted_text = self.web_scraper_service.extract_content_from_url(source.source_url)
        
        # Update source with extracted text
        source.raw_text = extracted_text
        source.processed_at = datetime.now()
        source.save()
        
        # Parse recipes from extracted text
        recipes = self.recipe_parser.parse_recipes_from_text(extracted_text)
        
        # Create extracted recipe records
        for recipe_data in recipes:
            ExtractedRecipe.objects.create(
                job=job,
                raw_name=recipe_data.get('name', 'Untitled Recipe'),
                raw_instructions=recipe_data.get('instructions', ''),
                raw_ingredients=recipe_data.get('ingredients', []),
                raw_metadata=recipe_data.get('metadata', {}),
                confidence_score=recipe_data.get('confidence', 0.0)
            )
        
        job.recipes_found = len(recipes)
        job.recipes_processed = len(recipes)
        job.save()
        
        self._log(job, f"Extracted {len(recipes)} recipes from URL", "info")
    
    def _process_text_source(self, job: IngestionJob, source: IngestionSource):
        """Process manual text input."""
        self._log(job, "Processing text source", "info")
        
        if not source.raw_text:
            raise ValueError("No text provided for text source")
        
        # Parse recipes from text
        recipes = self.recipe_parser.parse_recipes_from_text(source.raw_text)
        
        # Create extracted recipe records
        for recipe_data in recipes:
            ExtractedRecipe.objects.create(
                job=job,
                raw_name=recipe_data.get('name', 'Untitled Recipe'),
                raw_instructions=recipe_data.get('instructions', ''),
                raw_ingredients=recipe_data.get('ingredients', []),
                raw_metadata=recipe_data.get('metadata', {}),
                confidence_score=recipe_data.get('confidence', 0.0)
            )
        
        job.recipes_found = len(recipes)
        job.recipes_processed = len(recipes)
        job.save()
        
        self._log(job, f"Extracted {len(recipes)} recipes from text", "info")
    
    def _process_email_source(self, job: IngestionJob, source: IngestionSource):
        """Process email sources with attachments."""
        self._log(job, "Processing email source", "info")
        
        # This would typically be handled by the email service
        # For now, just process the raw text if available
        if source.raw_text:
            recipes = self.recipe_parser.parse_recipes_from_text(source.raw_text)
            
            # Create extracted recipe records
            for recipe_data in recipes:
                ExtractedRecipe.objects.create(
                    job=job,
                    raw_name=recipe_data.get('name', 'Untitled Recipe'),
                    raw_instructions=recipe_data.get('instructions', ''),
                    raw_ingredients=recipe_data.get('ingredients', []),
                    raw_metadata=recipe_data.get('metadata', {}),
                    confidence_score=recipe_data.get('confidence', 0.0)
                )
            
            job.recipes_found = len(recipes)
            job.recipes_processed = len(recipes)
            job.save()
            
            self._log(job, f"Extracted {len(recipes)} recipes from email", "info")
        else:
            self._log(job, "No text content found in email source", "warning")
    
    def _combine_paired_text(self, ingredients_text: str, directions_text: str) -> str:
        """
        Combine ingredients and directions text into a single recipe text.
        
        Args:
            ingredients_text: Text from ingredients photo
            directions_text: Text from directions photo
            
        Returns:
            Combined recipe text
        """
        lines = []
        
        # Add ingredients section
        if ingredients_text.strip():
            lines.append("INGREDIENTS:")
            lines.append(ingredients_text.strip())
            lines.append("")
        
        # Add directions section
        if directions_text.strip():
            lines.append("INSTRUCTIONS:")
            lines.append(directions_text.strip())
        
        return "\n".join(lines)
    
    def _log(self, job: IngestionJob, message: str, level: str = 'info'):
        """
        Log processing steps.
        
        Args:
            job: Ingestion job
            message: Log message
            level: Log level
        """
        ProcessingLog.objects.create(
            job=job,
            step='processing',
            message=message,
            level=level
        )
    
    def _log_paired(self, job: PairedPhotoJob, message: str, level: str = 'info'):
        """
        Log processing steps for paired photos.
        
        Args:
            job: Paired photo job
            message: Log message
            level: Log level
        """
        ProcessingLog.objects.create(
            job=job,
            step='paired_processing',
            message=message,
            level=level
        )
