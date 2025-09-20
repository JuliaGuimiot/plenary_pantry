import imaplib
import email
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from .models import (
    IngestionSource, IngestionJob, EmailIngestionSource, 
    EmailAttachment, ApprovedEmailSender, PairedPhotoSource, PairedPhotoJob
)
from .services import RecipeIngestionService

logger = logging.getLogger(__name__)


class EmailIngestionService:
    """Service for processing recipe emails and attachments"""
    
    def __init__(self):
        self.imap_server = settings.EMAIL_INGESTION_IMAP_SERVER
        self.imap_port = settings.EMAIL_INGESTION_IMAP_PORT
        self.email = settings.EMAIL_INGESTION_EMAIL
        self.password = settings.EMAIL_INGESTION_PASSWORD
        self.use_ssl = settings.EMAIL_INGESTION_USE_SSL
        self.folder = settings.EMAIL_INGESTION_FOLDER
        self.max_attachment_size = settings.EMAIL_INGESTION_MAX_ATTACHMENT_SIZE
        self.recipient_alias = getattr(settings, 'EMAIL_INGESTION_RECIPIENT_ALIAS', None)
        self.default_user = self._get_default_user()
    
    def _get_default_user(self):
        """Get the default user for email recipes"""
        from django.contrib.auth.models import User
        try:
            return User.objects.get(username=settings.EMAIL_INGESTION_DEFAULT_USER)
        except User.DoesNotExist:
            logger.error(f"Default user '{settings.EMAIL_INGESTION_DEFAULT_USER}' not found")
            return None
    
    def poll_emails(self) -> Dict[str, int]:
        """Poll for new emails and process recipe attachments"""
        stats = {
            'emails_processed': 0,
            'attachments_processed': 0,
            'recipes_created': 0,
            'errors': 0
        }
        
        if not self.email or not self.password:
            logger.warning("Email ingestion not configured - missing email or password")
            return stats
        
        try:
            # Connect to IMAP server
            with self._connect_to_imap() as mail:
                # Search for unread emails
                mail.select(self.folder)
                logger.info(f"Selected folder: {self.folder}")

                # First check for ALL emails to see what's available
                status_all, messages_all = mail.search(None, 'ALL')
                if status_all == 'OK':
                    all_email_ids = messages_all[0].split()
                    logger.info(f"Total emails in folder: {len(all_email_ids)}")
                    
                    # Debug: Show details of all emails
                    print(f"DEBUG: Found {len(all_email_ids)} total emails")
                    for i, email_id in enumerate(all_email_ids):
                        try:
                            status, msg_data = mail.fetch(email_id, '(RFC822.HEADER)')
                            if status == 'OK':
                                email_message = email.message_from_bytes(msg_data[0][1])
                                sender = email_message.get('From', 'Unknown')
                                subject = email_message.get('Subject', 'No Subject')
                                print(f"DEBUG: Email {i+1} (ID {email_id}): From={sender}, Subject={subject}")
                        except Exception as e:
                            print(f"DEBUG: Error fetching email {email_id}: {e}")
                
                # Then search for unread emails
                status, messages = mail.search(None, 'UNSEEN')
                logger.info(f"Search status: {status}, messages: {messages}")
                
                if status != 'OK':
                    logger.error("Failed to search for emails")
                    return stats
                
                email_ids = messages[0].split()
                logger.info(f"Found {len(email_ids)} unread emails")
                
                # If no unread emails, process recent emails for testing
                if len(email_ids) == 0 and len(all_email_ids) > 0:
                    logger.info("No unread emails found, processing recent emails for testing")
                    email_ids = [all_email_ids[-1]] if all_email_ids else []
                
                for email_id in email_ids:
                    try:
                        # Fetch email
                        status, msg_data = mail.fetch(email_id, '(RFC822)')
                        if status != 'OK':
                            continue
                        
                        # Parse email
                        email_body = msg_data[0][1]
                        email_message = email.message_from_bytes(email_body)
                        
                        # Debug logging
                        sender = email_message.get('From', 'Unknown')
                        subject = email_message.get('Subject', 'No Subject')
                        print(f"DEBUG: Processing email {email_id}: From={sender}, Subject={subject}")
                        logger.info(f"Processing email {email_id}: From={sender}, Subject={subject}")
                        
                        # Debug: Show all relevant headers
                        print(f"DEBUG: Email headers - From: {email_message.get('From')}")
                        print(f"DEBUG: Email headers - Reply-To: {email_message.get('Reply-To')}")
                        print(f"DEBUG: Email headers - X-Original-Sender: {email_message.get('X-Original-Sender')}")
                        print(f"DEBUG: Email headers - X-Forwarded-From: {email_message.get('X-Forwarded-From')}")
                        print(f"DEBUG: Email headers - Return-Path: {email_message.get('Return-Path')}")
                        
                        logger.info(f"Email headers - From: {email_message.get('From')}")
                        logger.info(f"Email headers - Reply-To: {email_message.get('Reply-To')}")
                        logger.info(f"Email headers - X-Original-Sender: {email_message.get('X-Original-Sender')}")
                        logger.info(f"Email headers - X-Forwarded-From: {email_message.get('X-Forwarded-From')}")
                        logger.info(f"Email headers - Return-Path: {email_message.get('Return-Path')}")
                        
                        # Check for attachments
                        attachment_count = 0
                        for part in email_message.walk():
                            if part.get_content_disposition() == 'attachment':
                                attachment_count += 1
                        print(f"DEBUG: Found {attachment_count} attachments in email")
                        logger.info(f"Found {attachment_count} attachments in email")
                        
                        # Process email
                        result = self._process_email(email_message)
                        stats['emails_processed'] += 1
                        stats['attachments_processed'] += result['attachments_processed']
                        stats['recipes_created'] += result['recipes_created']
                        stats['errors'] += result.get('errors', 0)
                        
                        # Mark email as read
                        mail.store(email_id, '+FLAGS', '\\Seen')
                        
                    except Exception as e:
                        logger.error(f"Error processing email {email_id}: {str(e)}")
                        stats['errors'] += 1
                        continue
                
        except Exception as e:
            logger.error(f"Email polling failed: {str(e)}")
            stats['errors'] += 1
        
        return stats
    
    def _connect_to_imap(self):
        """Connect to IMAP server"""
        if self.use_ssl:
            # For Proton Bridge, use STARTTLS instead of direct SSL
            if self.imap_server == '127.0.0.1' and self.imap_port == 1143:
                # Proton Bridge uses STARTTLS on localhost:1143
                mail = imaplib.IMAP4(self.imap_server, self.imap_port)
                mail.starttls()
            else:
                # Direct SSL for other providers
                mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        else:
            mail = imaplib.IMAP4(self.imap_server, self.imap_port)
        
        mail.login(self.email, self.password)
        return mail
    
    def _process_email(self, email_message) -> Dict[str, int]:
        """Process a single email for recipe attachments"""
        result = {
            'attachments_processed': 0,
            'recipes_created': 0
        }
        
        try:
            # Debug: Show all relevant headers first
            logger.info(f"=== EMAIL DEBUG INFO ===")
            logger.info(f"Email headers - From: {email_message.get('From')}")
            logger.info(f"Email headers - Reply-To: {email_message.get('Reply-To')}")
            logger.info(f"Email headers - X-Original-Sender: {email_message.get('X-Original-Sender')}")
            logger.info(f"Email headers - X-Forwarded-From: {email_message.get('X-Forwarded-From')}")
            logger.info(f"Email headers - Return-Path: {email_message.get('Return-Path')}")
            
            # Check for attachments
            attachment_count = 0
            for part in email_message.walk():
                if part.get_content_disposition() == 'attachment':
                    attachment_count += 1
            logger.info(f"Found {attachment_count} attachments in email")
            logger.info(f"=== END EMAIL DEBUG ===")
            
            # Extract email metadata
            sender_email = self._get_sender_email(email_message)
            sender_name = self._get_sender_name(email_message)
            subject = self._get_subject(email_message)
            message_id = email_message.get('Message-ID', '')
            received_at = self._parse_date(email_message.get('Date', ''))
            
            logger.info(f"Extracted sender_email: {sender_email}")
            logger.info(f"Extracted sender_name: {sender_name}")
            logger.info(f"Extracted subject: {subject}")
            
            # Debug: Show recipient information
            to_recipients = email_message.get_all('To', [])
            cc_recipients = email_message.get_all('Cc', [])
            bcc_recipients = email_message.get_all('Bcc', [])
            logger.info(f"Email recipients - To: {to_recipients}, Cc: {cc_recipients}, Bcc: {bcc_recipients}")
            logger.info(f"Looking for recipient alias: {self.recipient_alias}")
            
            # Check if we've already processed this email
            if EmailIngestionSource.objects.filter(message_id=message_id).exists():
                logger.info(f"Email {message_id} already processed, skipping")
                return result
            
            # Check if email is addressed to our recipient alias
            is_recipient_alias = self._is_recipient_alias(email_message)
            if not is_recipient_alias:
                logger.info(f"Email not addressed to recipient alias {self.recipient_alias}, skipping")
                return result
            
            # Check if sender is approved
            is_approved = self._is_approved_sender(sender_email)
            if not is_approved:
                logger.warning(f"Sender not on approved list: {sender_email}")
                return result
            
            # Get default user for recipes
            if not self.default_user:
                logger.error("No default user configured for email recipes")
                return result
            
            # Extract attachments
            attachments = self._extract_attachments(email_message)
            if not attachments:
                logger.info(f"No attachments found in email from {sender_email}")
                return result
            
            # Check if we should process as paired photos (2+ image attachments)
            image_attachments = [att for att in attachments if self._is_image_attachment_data(att)]
            if len(image_attachments) >= 2:
                logger.info(f"Found {len(image_attachments)} image attachments, processing as paired photos")
                paired_result = self.process_paired_photos_from_email(email_source, image_attachments)
                result['paired_sources_created'] = paired_result['paired_sources_created']
                result['recipes_created'] = paired_result['recipes_created']
                result['errors'] = paired_result['errors']
                return result
            
            # Create ingestion source
            with transaction.atomic():
                source = IngestionSource.objects.create(
                    user=self.default_user,
                    source_type='email',
                    source_name=f"Email from {sender_name or sender_email}",
                    raw_text=self._extract_email_text(email_message)
                )
                
                # Create email source details
                email_source = EmailIngestionSource.objects.create(
                    source=source,
                    sender_email=sender_email,
                    sender_name=sender_name,
                    subject=subject,
                    received_at=received_at,
                    message_id=message_id,
                    raw_email_content=str(email_message),
                    attachment_count=len(attachments),
                    is_approved_sender=True
                )
                
                # Process attachments and embedded images
                attachment_count = sum(1 for a in attachments if a['type'] == 'attachment')
                embedded_count = sum(1 for a in attachments if a['type'] == 'embedded')
                logger.info(f"Processing {len(attachments)} items ({attachment_count} attachments, {embedded_count} embedded images)")
                
                for i, attachment_data in enumerate(attachments):
                    try:
                        item_type = attachment_data.get('type', 'attachment')
                        filename = attachment_data['filename']
                        content_type = attachment_data['content_type']
                        size = attachment_data['size']
                        
                        logger.info(f"🔄 Processing {item_type} {i+1}/{len(attachments)}: {filename}")
                        logger.info(f"   📄 Content-Type: {content_type}, Size: {size} bytes")
                        
                        attachment = self._save_attachment(email_source, attachment_data)
                        if attachment:
                            result['attachments_processed'] += 1
                            logger.info(f"✅ Successfully saved {item_type}: {filename}")
                            
                            # Process the attachment as a recipe
                            if self._is_image_attachment(attachment):
                                logger.info(f"🖼️  Processing image {item_type} as recipe: {filename}")
                                try:
                                    recipe_count = self._process_attachment_as_recipe(attachment)
                                    result['recipes_created'] += recipe_count
                                    if recipe_count > 0:
                                        logger.info(f"🎉 Created {recipe_count} recipes from {item_type}: {filename}")
                                    else:
                                        logger.warning(f"⚠️  No recipes extracted from {item_type}: {filename}")
                                except Exception as recipe_error:
                                    logger.error(f"❌ Recipe processing failed for {item_type} {filename}: {str(recipe_error)}")
                                    logger.error(f"   📊 Error type: {type(recipe_error).__name__}")
                                    result['errors'] = result.get('errors', 0) + 1
                            else:
                                logger.info(f"⏭️  Skipping non-image {item_type}: {filename} ({content_type})")
                        else:
                            logger.error(f"❌ Failed to save {item_type}: {filename}")
                            result['errors'] = result.get('errors', 0) + 1
                    except Exception as e:
                        logger.error(f"💥 Error processing {attachment_data.get('type', 'item')} {attachment_data.get('filename', 'unknown')}: {str(e)}")
                        logger.error(f"   📊 Error details: {type(e).__name__}: {str(e)}")
                        result['errors'] = result.get('errors', 0) + 1
                
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            raise
        
        return result
    
    def _get_sender_email(self, email_message) -> str:
        """Extract sender email address"""
        sender = email_message.get('From', '')
        if '<' in sender and '>' in sender:
            # Extract email from "Name <email@domain.com>" format
            start = sender.find('<') + 1
            end = sender.find('>')
            return sender[start:end].strip()
        return sender.strip()
    
    def _get_sender_name(self, email_message) -> str:
        """Extract sender name"""
        sender = email_message.get('From', '')
        if '<' in sender and '>' in sender:
            # Extract name from "Name <email@domain.com>" format
            name = sender[:sender.find('<')].strip()
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1]
            return name
        return ''
    
    def _get_subject(self, email_message) -> str:
        """Extract and decode email subject"""
        subject = email_message.get('Subject', '')
        decoded_parts = decode_header(subject)
        decoded_subject = ''
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    decoded_subject += part.decode(encoding)
                else:
                    decoded_subject += part.decode('utf-8', errors='ignore')
            else:
                decoded_subject += part
        
        return decoded_subject
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse email date string"""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            return datetime.now()
    
    def _is_approved_sender(self, sender_email: str) -> bool:
        """Check if sender email is on the approved list"""
        try:
            return ApprovedEmailSender.objects.filter(
                email_address__iexact=sender_email,
                is_active=True
            ).exists()
        except Exception as e:
            logger.error(f"Error checking approved sender: {str(e)}")
            return False
    
    def _is_recipient_alias(self, email_message) -> bool:
        """Check if email is addressed to our recipient alias"""
        if not self.recipient_alias:
            return True  # If no alias specified, accept all emails
        
        # Check To, Cc, and Bcc fields
        to_recipients = email_message.get_all('To', [])
        cc_recipients = email_message.get_all('Cc', [])
        bcc_recipients = email_message.get_all('Bcc', [])
        
        all_recipients = to_recipients + cc_recipients + bcc_recipients
        
        for recipient in all_recipients:
            # Parse email address from "Name <email@domain.com>" format
            if '<' in recipient and '>' in recipient:
                email_part = recipient.split('<')[1].split('>')[0].strip()
            else:
                email_part = recipient.strip()
            
            if email_part.lower() == self.recipient_alias.lower():
                return True
        
        return False
    
    def _extract_attachments(self, email_message) -> List[Dict]:
        """Extract attachments and embedded images from email"""
        attachments = []
        
        logger.info("Extracting attachments and embedded images from email...")
        for part in email_message.walk():
            # Check for traditional attachments
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    # Decode filename if needed
                    decoded_parts = decode_header(filename)
                    decoded_filename = ''
                    for part_data, encoding in decoded_parts:
                        if isinstance(part_data, bytes):
                            if encoding:
                                decoded_filename += part_data.decode(encoding)
                            else:
                                decoded_filename += part_data.decode('utf-8', errors='ignore')
                        else:
                            decoded_filename += part_data
                    
                    logger.info(f"Found attachment: {decoded_filename} ({part.get_content_type()})")
                    
                    # Get attachment data
                    attachment_data = part.get_payload(decode=True)
                    if attachment_data and len(attachment_data) <= self.max_attachment_size:
                        attachments.append({
                            'filename': decoded_filename,
                            'content_type': part.get_content_type(),
                            'data': attachment_data,
                            'size': len(attachment_data),
                            'type': 'attachment'
                        })
                        logger.info(f"Added attachment: {decoded_filename} ({len(attachment_data)} bytes)")
                    else:
                        if not attachment_data:
                            logger.warning(f"Attachment {decoded_filename} is empty, skipping")
                        else:
                            logger.warning(f"Attachment {decoded_filename} too large ({len(attachment_data)} bytes), skipping")
                else:
                    logger.warning("Found attachment with no filename, skipping")
            
            # Check for embedded/inline images
            elif (part.get_content_type() and 
                  part.get_content_type().startswith('image/') and 
                  part.get_content_disposition() == 'inline'):
                
                logger.info(f"Found inline image part: {part.get_content_type()}")
                
                # Try to get filename from Content-ID or Content-Location
                filename = part.get_filename()
                content_id = part.get('Content-ID', '')
                content_location = part.get('Content-Location', '')
                
                logger.info(f"Embedded image identifiers - Filename: {filename}, Content-ID: {content_id}, Content-Location: {content_location}")
                
                if not filename:
                    # Try Content-ID
                    if content_id:
                        filename = content_id.strip('<>') + '.jpg'  # Default extension
                        logger.info(f"Using Content-ID for filename: {filename}")
                    else:
                        # Try Content-Location
                        if content_location:
                            filename = content_location
                            logger.info(f"Using Content-Location for filename: {filename}")
                        else:
                            filename = f"embedded_image_{len(attachments) + 1}.jpg"
                            logger.info(f"Generated default filename: {filename}")
                
                logger.info(f"Processing embedded image: {filename} ({part.get_content_type()})")
                
                # Get image data
                image_data = part.get_payload(decode=True)
                if image_data and len(image_data) <= self.max_attachment_size:
                    attachments.append({
                        'filename': filename,
                        'content_type': part.get_content_type(),
                        'data': image_data,
                        'size': len(image_data),
                        'type': 'embedded'
                    })
                    logger.info(f"✅ Successfully added embedded image: {filename} ({len(image_data)} bytes)")
                else:
                    if not image_data:
                        logger.warning(f"❌ Embedded image {filename} is empty, skipping")
                    else:
                        logger.warning(f"❌ Embedded image {filename} too large ({len(image_data)} bytes), skipping")
        
        logger.info(f"Extracted {len(attachments)} total items ({sum(1 for a in attachments if a['type'] == 'attachment')} attachments, {sum(1 for a in attachments if a['type'] == 'embedded')} embedded images)")
        return attachments
    
    def _save_attachment(self, email_source: EmailIngestionSource, attachment_data: Dict) -> Optional[EmailAttachment]:
        """Save email attachment to database"""
        try:
            filename = attachment_data['filename']
            content_type = attachment_data['content_type']
            size = attachment_data['size']
            attachment_type = attachment_data.get('type', 'attachment')
            
            logger.info(f"💾 Saving {attachment_type} to database: {filename}")
            logger.info(f"   📊 Details: {content_type}, {size} bytes")
            
            # Create file content with proper name attribute
            file_content = ContentFile(attachment_data['data'], name=filename)
            
            # Create attachment record
            attachment = EmailAttachment.objects.create(
                email_source=email_source,
                filename=filename,
                content_type=content_type,
                file_size=size,
                attachment_file=file_content,
                attachment_type=attachment_type
            )
            
            logger.info(f"✅ Successfully saved {attachment_type} to database: {filename} (ID: {attachment.id})")
            return attachment
            
        except Exception as e:
            logger.error(f"❌ Error saving {attachment_data.get('type', 'attachment')} {attachment_data['filename']}: {str(e)}")
            logger.error(f"   📊 Error type: {type(e).__name__}")
            logger.error(f"   📊 Error details: {str(e)}")
            return None
    
    def _is_image_attachment(self, attachment: EmailAttachment) -> bool:
        """Check if attachment is an image"""
        image_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/heic', 'image/heif']
        return attachment.content_type.lower() in image_types
    
    def _process_attachment_as_recipe(self, attachment: EmailAttachment) -> int:
        """Process image attachment as recipe"""
        try:
            logger.info(f"🍳 Starting recipe processing for {attachment.attachment_type}: {attachment.filename}")
            
            # Create a temporary ingestion source for the attachment
            temp_source = IngestionSource.objects.create(
                user=self.default_user,
                source_type='image',
                source_name=f"Email {attachment.attachment_type}: {attachment.filename}",
                source_file=attachment.attachment_file
            )
            
            logger.info(f"📝 Created ingestion source: {temp_source.id}")
            
            # Process the source
            service = RecipeIngestionService(self.default_user)
            job = service.process_source(temp_source)
            
            logger.info(f"🔄 Processing job created: {job.id} (Status: {job.status})")
            
            # Auto-normalize recipes
            saved_recipes = []
            if job.extracted_recipes.exists():
                logger.info(f"📋 Found {job.extracted_recipes.count()} extracted recipes, normalizing...")
                try:
                    saved_recipes = service.normalize_and_save_recipes(job)
                    logger.info(f"✅ Successfully normalized {len(saved_recipes)} recipes")
                except Exception as e:
                    logger.error(f"❌ Auto-normalization failed for {attachment.attachment_type} {attachment.filename}: {str(e)}")
                    logger.error(f"   📊 Error type: {type(e).__name__}")
            else:
                logger.warning(f"⚠️  No recipes extracted from {attachment.attachment_type}: {attachment.filename}")
            
            # Mark attachment as processed
            attachment.is_processed = True
            attachment.save()
            
            logger.info(f"✅ Completed processing {attachment.attachment_type}: {attachment.filename} -> {len(saved_recipes)} recipes")
            return len(saved_recipes)
            
        except Exception as e:
            logger.error(f"💥 Error processing {attachment.attachment_type} {attachment.filename} as recipe: {str(e)}")
            logger.error(f"   📊 Error type: {type(e).__name__}")
            logger.error(f"   📊 Error details: {str(e)}")
            attachment.processing_error = str(e)
            attachment.save()
            return 0
    
    def _extract_email_text(self, email_message) -> str:
        """Extract text content from email"""
        text_content = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        text_content += payload.decode('utf-8', errors='ignore')
        else:
            payload = email_message.get_payload(decode=True)
            if payload:
                text_content = payload.decode('utf-8', errors='ignore')
        
        return text_content
    
    def process_paired_photos_from_email(self, email_source: EmailIngestionSource, attachments: List[Dict]) -> Dict[str, int]:
        """Process paired photos from email attachments"""
        result = {
            'paired_sources_created': 0,
            'recipes_created': 0,
            'errors': 0
        }
        
        try:
            # Group attachments by potential pairing (based on filename patterns or order)
            paired_groups = self._group_attachments_for_pairing(attachments)
            
            for group in paired_groups:
                try:
                    # Create paired photo source
                    paired_source = self._create_paired_source_from_email(email_source, group)
                    if not paired_source:
                        continue
                    
                    result['paired_sources_created'] += 1
                    
                    # Process the paired photos
                    service = RecipeIngestionService(self.default_user)
                    job = service.process_paired_photos(paired_source)
                    
                    if job.recipes_found > 0:
                        result['recipes_created'] += job.recipes_found
                        logger.info(f"✅ Created {job.recipes_found} recipes from paired photos")
                    else:
                        logger.warning(f"⚠️  No recipes extracted from paired photos")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing paired photo group: {str(e)}")
                    result['errors'] += 1
                    continue
                    
        except Exception as e:
            logger.error(f"💥 Error in paired photo processing: {str(e)}")
            result['errors'] += 1
        
        return result
    
    def _group_attachments_for_pairing(self, attachments: List[Dict]) -> List[List[Dict]]:
        """Group attachments into potential pairs for ingredients/directions"""
        groups = []
        
        # Simple grouping: pair consecutive image attachments
        image_attachments = [att for att in attachments if self._is_image_attachment_data(att)]
        
        # Group in pairs
        for i in range(0, len(image_attachments), 2):
            if i + 1 < len(image_attachments):
                groups.append([image_attachments[i], image_attachments[i + 1]])
            else:
                # Single remaining image - create a group with just one
                groups.append([image_attachments[i]])
        
        return groups
    
    def _is_image_attachment_data(self, attachment_data: Dict) -> bool:
        """Check if attachment data represents an image"""
        image_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/heic', 'image/heif']
        return attachment_data.get('content_type', '').lower() in image_types
    
    def _create_paired_source_from_email(self, email_source: EmailIngestionSource, attachment_group: List[Dict]) -> Optional[PairedPhotoSource]:
        """Create a paired photo source from email attachments"""
        try:
            if len(attachment_group) < 1:
                return None
            
            # Generate pairing token
            import uuid
            pairing_token = str(uuid.uuid4())[:8]
            
            # Create paired source
            paired_source = PairedPhotoSource.objects.create(
                user=self.default_user,
                pairing_token=pairing_token,
                recipe_name=f"Email Recipe from {email_source.sender_name or email_source.sender_email}",
                is_test=False
            )
            
            # Assign first attachment as ingredients, second as directions
            if len(attachment_group) >= 1:
                ingredients_data = attachment_group[0]
                ingredients_file = ContentFile(ingredients_data['data'], name=ingredients_data['filename'])
                paired_source.ingredients_photo = ingredients_file
                paired_source.status = 'ingredients_uploaded'
            
            if len(attachment_group) >= 2:
                directions_data = attachment_group[1]
                directions_file = ContentFile(directions_data['data'], name=directions_data['filename'])
                paired_source.directions_photo = directions_file
                paired_source.status = 'directions_uploaded'
            
            paired_source.save()
            
            logger.info(f"✅ Created paired photo source: {pairing_token}")
            return paired_source
            
        except Exception as e:
            logger.error(f"❌ Error creating paired source from email: {str(e)}")
            return None
