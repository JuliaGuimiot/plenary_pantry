from django.core.management.base import BaseCommand
from django.utils import timezone
from recipe_ingestion.email_service import EmailIngestionService
import time


class Command(BaseCommand):
    help = 'Poll emails for recipe attachments and process them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run once and exit (default: run continuously)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=300,
            help='Polling interval in seconds (default: 300)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )

    def handle(self, *args, **options):
        once = options['once']
        interval = options['interval']
        verbose = options['verbose']
        
        email_service = EmailIngestionService()
        
        if verbose:
            self.stdout.write(
                self.style.SUCCESS('Starting email polling service...')
            )
            self.stdout.write(f"Polling interval: {interval} seconds")
            self.stdout.write(f"Run once: {once}")
        
        try:
            while True:
                start_time = timezone.now()
                
                if verbose:
                    self.stdout.write(f"\n[{start_time}] Polling for new emails...")
                
                # Poll for emails
                stats = email_service.poll_emails()
                
                # Display enhanced results
                if verbose or any(stats.values()):
                    self.stdout.write("=" * 60)
                    self.stdout.write(self.style.SUCCESS("📧 EMAIL POLLING SUMMARY"))
                    self.stdout.write("=" * 60)
                    self.stdout.write(f"📨 Emails processed: {stats['emails_processed']}")
                    self.stdout.write(f"📎 Attachments processed: {stats['attachments_processed']}")
                    self.stdout.write(f"🍳 Recipes created: {stats['recipes_created']}")
                    self.stdout.write(f"❌ Errors encountered: {stats['errors']}")
                    
                    if stats['errors'] > 0:
                        self.stdout.write(
                            self.style.WARNING(f"⚠️  {stats['errors']} errors occurred during processing - check logs above for details")
                        )
                    else:
                        self.stdout.write(self.style.SUCCESS("✅ All processing completed successfully!"))
                    
                    self.stdout.write("=" * 60)
                
                if once:
                    break
                
                # Wait for next poll
                elapsed = (timezone.now() - start_time).total_seconds()
                sleep_time = max(0, interval - elapsed)
                
                if verbose and sleep_time > 0:
                    self.stdout.write(f"Sleeping for {sleep_time:.1f} seconds...")
                
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\nEmail polling stopped by user')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Email polling failed: {str(e)}')
            )
            raise
