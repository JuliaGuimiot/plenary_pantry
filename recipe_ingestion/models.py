from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import uuid


class IngestionSource(models.Model):
    """Track the source of recipe ingestion"""
    SOURCE_TYPES = [
        ('image', 'Image Upload'),
        ('multi_image', 'Multi-Image Upload'),
        ('url', 'Web URL'),
        ('text', 'Manual Text Input'),
        ('api', 'API Import'),
        ('email', 'Email Attachment'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ingestion_sources')
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    source_name = models.CharField(max_length=200, help_text="Name or title of the source")
    source_url = models.URLField(blank=True, null=True)
    source_file = models.FileField(
        upload_to='recipe_sources/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf'])]
    )
    raw_text = models.TextField(blank=True, help_text="Raw text extracted from source")
    is_test = models.BooleanField(default=False, help_text="Mark as test data for easy filtering")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        test_marker = " [TEST]" if self.is_test else ""
        return f"{self.source_name} ({self.get_source_type_display()}){test_marker}"


class IngestionJob(models.Model):
    """Track the processing of recipe ingestion"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partially Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(IngestionSource, on_delete=models.CASCADE, related_name='jobs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    recipes_found = models.PositiveIntegerField(default=0)
    recipes_processed = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Job {self.id} - {self.status}"


class ExtractedRecipe(models.Model):
    """Raw recipe data extracted from sources before normalization"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE, related_name='extracted_recipes')
    raw_name = models.CharField(max_length=200)
    raw_instructions = models.TextField()
    raw_ingredients = models.JSONField(default=list, help_text="List of raw ingredient strings")
    raw_metadata = models.JSONField(default=dict, help_text="Additional extracted metadata")
    confidence_score = models.FloatField(default=0.0, help_text="Confidence in extraction quality (0-1)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Extracted: {self.raw_name}"


class IngredientMapping(models.Model):
    """Map raw ingredient text to normalized ingredients"""
    raw_text = models.CharField(max_length=500)
    normalized_ingredient = models.ForeignKey('core.Ingredient', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    unit = models.ForeignKey('core.Unit', on_delete=models.CASCADE, null=True, blank=True)
    preparation_method = models.CharField(max_length=200, blank=True)
    confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['raw_text', 'normalized_ingredient']
    
    def __str__(self):
        return f"{self.raw_text} -> {self.normalized_ingredient}"


class MultiImageSource(models.Model):
    """Track multiple images for a single recipe source"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(IngestionSource, on_delete=models.CASCADE, related_name='multi_images')
    image_file = models.FileField(
        upload_to='recipe_sources/multi/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'heic', 'heif'])]
    )
    page_number = models.PositiveIntegerField(default=1, help_text="Page number in the recipe")
    page_type = models.CharField(
        max_length=20, 
        choices=[
            ('ingredients', 'Ingredients Page'),
            ('instructions', 'Instructions Page'),
            ('metadata', 'Metadata Page'),
            ('unknown', 'Unknown'),
        ],
        default='unknown',
        help_text="Type of content on this page"
    )
    extracted_text = models.TextField(blank=True, help_text="Text extracted from this image")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['page_number']
    
    def __str__(self):
        return f"{self.source.source_name} - Page {self.page_number} ({self.get_page_type_display()})"


class RecipeTemplate(models.Model):
    """Templates for different recipe formats to improve extraction"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    pattern = models.TextField(help_text="Regex pattern or extraction rules")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class ProcessingLog(models.Model):
    """Log processing steps and decisions"""
    job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE, related_name='logs')
    step = models.CharField(max_length=100)
    message = models.TextField()
    level = models.CharField(max_length=20, choices=[
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ], default='info')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.job.id} - {self.step}: {self.message}"


class ApprovedEmailSender(models.Model):
    """Approved email addresses that can send recipes to the system"""
    email_address = models.EmailField(unique=True, help_text="Email address that can send recipes")
    sender_name = models.CharField(max_length=200, blank=True, help_text="Optional name for the sender")
    is_active = models.BooleanField(default=True, help_text="Whether this sender is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Approved Email Sender"
        verbose_name_plural = "Approved Email Senders"
        ordering = ['email_address']
    
    def __str__(self):
        name = f" ({self.sender_name})" if self.sender_name else ""
        return f"{self.email_address}{name}"


class EmailIngestionSource(models.Model):
    """Track email-based recipe ingestion sources"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(IngestionSource, on_delete=models.CASCADE, related_name='email_details')
    sender_email = models.EmailField(help_text="Email address of the sender")
    sender_name = models.CharField(max_length=200, blank=True, help_text="Name of the sender")
    subject = models.CharField(max_length=500, help_text="Email subject line")
    received_at = models.DateTimeField(help_text="When the email was received")
    message_id = models.CharField(max_length=500, unique=True, help_text="Email message ID for deduplication")
    raw_email_content = models.TextField(blank=True, help_text="Raw email content for debugging")
    attachment_count = models.PositiveIntegerField(default=0, help_text="Number of attachments processed")
    is_approved_sender = models.BooleanField(default=False, help_text="Whether sender was on approved list")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Email Ingestion Source"
        verbose_name_plural = "Email Ingestion Sources"
        ordering = ['-received_at']
    
    def __str__(self):
        return f"Email from {self.sender_email} - {self.subject}"


class EmailAttachment(models.Model):
    """Track individual email attachments for recipe processing"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email_source = models.ForeignKey(EmailIngestionSource, on_delete=models.CASCADE, related_name='attachments')
    filename = models.CharField(max_length=500, help_text="Original filename of the attachment")
    content_type = models.CharField(max_length=100, help_text="MIME type of the attachment")
    file_size = models.PositiveIntegerField(help_text="Size of the attachment in bytes")
    attachment_file = models.FileField(
        upload_to='recipe_sources/email/',
        help_text="Saved attachment file"
    )
    is_processed = models.BooleanField(default=False, help_text="Whether this attachment has been processed")
    processing_error = models.TextField(blank=True, help_text="Error message if processing failed")
    attachment_type = models.CharField(
        max_length=20, 
        choices=[('attachment', 'Attachment'), ('embedded', 'Embedded Image')],
        default='attachment',
        help_text="Type of attachment - traditional attachment or embedded image"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Email Attachment"
        verbose_name_plural = "Email Attachments"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.filename} ({self.content_type})"


class PairedPhotoSource(models.Model):
    """Track paired photo uploads for ingredients and directions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('ingredients_uploaded', 'Ingredients Uploaded'),
        ('directions_uploaded', 'Directions Uploaded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paired_photo_sources')
    pairing_token = models.CharField(max_length=100, unique=True, help_text="Token to link ingredients and directions photos")
    recipe_name = models.CharField(max_length=200, blank=True, help_text="Recipe name if provided")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    ingredients_photo = models.FileField(
        upload_to='recipe_sources/paired/ingredients/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'heic', 'heif'])]
    )
    directions_photo = models.FileField(
        upload_to='recipe_sources/paired/directions/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'heic', 'heif'])]
    )
    ingredients_text = models.TextField(blank=True, help_text="Extracted text from ingredients photo")
    directions_text = models.TextField(blank=True, help_text="Extracted text from directions photo")
    combined_text = models.TextField(blank=True, help_text="Combined text from both photos")
    is_test = models.BooleanField(default=False, help_text="Mark as test data for easy filtering")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Paired Photo Source"
        verbose_name_plural = "Paired Photo Sources"
        ordering = ['-created_at']
    
    def __str__(self):
        test_marker = " [TEST]" if self.is_test else ""
        return f"Paired Photos: {self.recipe_name or 'Untitled'}{test_marker} ({self.status})"
    
    def is_complete(self):
        """Check if both photos are uploaded"""
        return bool(self.ingredients_photo and self.directions_photo)
    
    def can_process(self):
        """Check if ready for processing"""
        return self.is_complete() and self.status in ['ingredients_uploaded', 'directions_uploaded']


class PairedPhotoJob(models.Model):
    """Track processing of paired photo sources"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paired_source = models.ForeignKey(PairedPhotoSource, on_delete=models.CASCADE, related_name='jobs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    recipes_found = models.PositiveIntegerField(default=0)
    recipes_processed = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Paired Job {self.id} - {self.status}"
