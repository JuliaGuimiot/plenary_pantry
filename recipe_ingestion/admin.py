from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    IngestionSource, IngestionJob, ExtractedRecipe, IngredientMapping,
    MultiImageSource, RecipeTemplate, ProcessingLog, ApprovedEmailSender,
    EmailIngestionSource, EmailAttachment
)


@admin.register(IngestionSource)
class IngestionSourceAdmin(admin.ModelAdmin):
    list_display = ['source_name', 'source_type', 'user', 'created_at', 'processed_at', 'is_test']
    list_filter = ['source_type', 'is_test', 'created_at', 'processed_at']
    search_fields = ['source_name', 'user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'processed_at']
    date_hierarchy = 'created_at'


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'source', 'status', 'recipes_found', 'recipes_processed', 'started_at', 'completed_at']
    list_filter = ['status', 'started_at', 'completed_at']
    search_fields = ['source__source_name', 'source__user__username']
    readonly_fields = ['id', 'started_at', 'completed_at']
    date_hierarchy = 'started_at'


@admin.register(ExtractedRecipe)
class ExtractedRecipeAdmin(admin.ModelAdmin):
    list_display = ['raw_name', 'job', 'confidence_score', 'created_at']
    list_filter = ['confidence_score', 'created_at']
    search_fields = ['raw_name', 'job__source__source_name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(IngredientMapping)
class IngredientMappingAdmin(admin.ModelAdmin):
    list_display = ['raw_text', 'normalized_ingredient', 'quantity', 'unit', 'confidence', 'created_at']
    list_filter = ['confidence', 'created_at']
    search_fields = ['raw_text', 'normalized_ingredient__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(MultiImageSource)
class MultiImageSourceAdmin(admin.ModelAdmin):
    list_display = ['source', 'page_number', 'page_type', 'created_at']
    list_filter = ['page_type', 'created_at']
    search_fields = ['source__source_name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(RecipeTemplate)
class RecipeTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(ProcessingLog)
class ProcessingLogAdmin(admin.ModelAdmin):
    list_display = ['job', 'step', 'level', 'created_at']
    list_filter = ['level', 'step', 'created_at']
    search_fields = ['job__id', 'message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(ApprovedEmailSender)
class ApprovedEmailSenderAdmin(admin.ModelAdmin):
    list_display = ['email_address', 'sender_name', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['email_address', 'sender_name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(EmailIngestionSource)
class EmailIngestionSourceAdmin(admin.ModelAdmin):
    list_display = ['sender_email', 'sender_name', 'subject', 'attachment_count', 'is_approved_sender', 'received_at', 'source_link']
    list_filter = ['received_at', 'attachment_count', 'is_approved_sender']
    search_fields = ['sender_email', 'sender_name', 'subject', 'message_id']
    readonly_fields = ['id', 'received_at', 'message_id', 'raw_email_content', 'created_at']
    date_hierarchy = 'received_at'
    
    def source_link(self, obj):
        url = reverse('admin:recipe_ingestion_ingestionsource_change', args=[obj.source.id])
        return format_html('<a href="{}">{}</a>', url, obj.source.source_name)
    source_link.short_description = 'Source'


@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'attachment_type', 'content_type', 'file_size', 'is_processed', 'email_source', 'created_at']
    list_filter = ['attachment_type', 'content_type', 'is_processed', 'created_at']
    search_fields = ['filename', 'email_source__sender_email']
    readonly_fields = ['id', 'file_size', 'created_at']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('email_source__source__user')
