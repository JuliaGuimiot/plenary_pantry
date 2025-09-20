"""
OCR Service for image processing and text extraction.

This service handles all OCR-related operations including image preprocessing,
text extraction, and multi-image text processing.
"""

import logging
from typing import List, Optional

import pytesseract
from PIL import Image
import cv2
import numpy as np

from ..utils.constants import RecipeProcessingConfig

logger = logging.getLogger(__name__)


class OCRService:
    """Service for OCR operations and image text extraction."""
    
    def __init__(self):
        """Initialize the OCR service."""
        self.confidence_threshold = RecipeProcessingConfig.OCR_CONFIDENCE_THRESHOLD
    
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text from the image
        """
        try:
            # Load and preprocess image
            image = self._preprocess_image(image_path)
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(image, config='--psm 6')
            
            # Clean up the text
            cleaned_text = self._clean_extracted_text(text)
            
            logger.info(f"OCR extracted {len(cleaned_text)} characters from {image_path}")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}", exc_info=True)
            raise
    
    def extract_text_from_multiple_images(self, image_paths: List[str]) -> str:
        """
        Extract text from multiple images and combine.
        
        Args:
            image_paths: List of paths to image files
            
        Returns:
            Combined extracted text from all images
        """
        all_text = []
        
        for i, image_path in enumerate(image_paths):
            try:
                text = self.extract_text_from_image(image_path)
                if text.strip():
                    all_text.append(f"--- Page {i+1} ---\n{text}")
            except Exception as e:
                logger.warning(f"Failed to extract text from image {i+1}: {str(e)}")
                all_text.append(f"--- Page {i+1} ---\n[OCR extraction failed]")
        
        return "\n\n".join(all_text)
    
    def _preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR results.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Preprocessed image as numpy array
        """
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Apply morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean up extracted text for better parsing.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 2:  # Skip very short lines
                cleaned_lines.append(line)
        
        # Join lines and clean up
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Remove common OCR artifacts
        cleaned_text = cleaned_text.replace('|', 'I')  # Common OCR mistake
        cleaned_text = cleaned_text.replace('0', 'O')  # In certain contexts
        
        return cleaned_text
    
    def clean_multi_image_text(self, text: str) -> str:
        """
        Clean up text from multi-image sources for better parsing.
        
        Args:
            text: Combined text from multiple images
            
        Returns:
            Cleaned and organized text
        """
        if not text:
            return ""
        
        # Split by page markers
        pages = text.split('--- Page')
        cleaned_pages = []
        
        for i, page in enumerate(pages):
            if not page.strip():
                continue
                
            # Clean each page
            page = page.strip()
            if page.startswith(' '):
                page = page[1:]  # Remove leading space from page marker
            
            # Remove page markers from content
            page = page.replace(f'{i+1} ---', '').strip()
            
            if page:
                cleaned_pages.append(page)
        
        # Combine pages with clear separation
        if len(cleaned_pages) > 1:
            return '\n\n'.join(cleaned_pages)
        else:
            return cleaned_pages[0] if cleaned_pages else ""
    
    def get_ocr_confidence(self, image_path: str) -> float:
        """
        Get OCR confidence score for an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Confidence score between 0 and 1
        """
        try:
            image = self._preprocess_image(image_path)
            
            # Get detailed OCR data
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            
            if not confidences:
                return 0.0
            
            avg_confidence = sum(confidences) / len(confidences)
            return avg_confidence / 100.0  # Convert to 0-1 scale
            
        except Exception as e:
            logger.warning(f"Could not calculate OCR confidence: {str(e)}")
            return 0.0
