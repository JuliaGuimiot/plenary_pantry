from django.core.management.base import BaseCommand
from recipe_ingestion.models import ApprovedEmailSender


class Command(BaseCommand):
    help = 'Manage approved email senders for recipe ingestion'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all approved email senders',
        )
        parser.add_argument(
            '--add',
            type=str,
            help='Add approved sender (format: email@domain.com or "Name <email@domain.com>")',
        )
        parser.add_argument(
            '--remove',
            type=str,
            help='Remove approved sender by email address',
        )
        parser.add_argument(
            '--activate',
            type=str,
            help='Activate approved sender by email address',
        )
        parser.add_argument(
            '--deactivate',
            type=str,
            help='Deactivate approved sender by email address',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_senders()
        elif options['add']:
            self.add_sender(options['add'])
        elif options['remove']:
            self.remove_sender(options['remove'])
        elif options['activate']:
            self.activate_sender(options['activate'])
        elif options['deactivate']:
            self.deactivate_sender(options['deactivate'])
        else:
            self.stdout.write(
                self.style.ERROR('Please specify an action: --list, --add, --remove, --activate, or --deactivate')
            )

    def list_senders(self):
        """List all approved email senders"""
        senders = ApprovedEmailSender.objects.all().order_by('email_address')
        
        if not senders:
            self.stdout.write(self.style.WARNING('No approved email senders found'))
            return
        
        self.stdout.write(self.style.SUCCESS('Approved Email Senders:'))
        self.stdout.write('-' * 80)
        
        for sender in senders:
            status = 'ACTIVE' if sender.is_active else 'INACTIVE'
            name = f" ({sender.sender_name})" if sender.sender_name else ""
            self.stdout.write(
                f"{sender.email_address:<40} | {status:<8} | {sender.created_at.strftime('%Y-%m-%d %H:%M')}{name}"
            )

    def add_sender(self, sender_str):
        """Add a new approved sender"""
        try:
            # Parse sender string - could be just email or "Name <email>"
            if '<' in sender_str and '>' in sender_str:
                # Extract name and email from "Name <email@domain.com>" format
                start = sender_str.find('<') + 1
                end = sender_str.find('>')
                email = sender_str[start:end].strip()
                name = sender_str[:sender_str.find('<')].strip()
                if name.startswith('"') and name.endswith('"'):
                    name = name[1:-1]
            else:
                # Just email address
                email = sender_str.strip()
                name = ''
            
            # Validate email format
            if '@' not in email or '.' not in email.split('@')[1]:
                self.stdout.write(
                    self.style.ERROR(f'Invalid email format: {email}')
                )
                return
            
            # Check if email already exists
            if ApprovedEmailSender.objects.filter(email_address__iexact=email).exists():
                self.stdout.write(
                    self.style.ERROR(f'Email "{email}" is already in the approved list')
                )
                return
            
            # Create approved sender
            sender = ApprovedEmailSender.objects.create(
                email_address=email,
                sender_name=name
            )
            
            name_display = f" ({name})" if name else ""
            self.stdout.write(
                self.style.SUCCESS(f'Approved sender added: {email}{name_display}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error adding approved sender: {str(e)}')
            )

    def remove_sender(self, email):
        """Remove an approved sender"""
        try:
            sender = ApprovedEmailSender.objects.get(email_address__iexact=email)
            name_display = f" ({sender.sender_name})" if sender.sender_name else ""
            sender.delete()
            
            self.stdout.write(
                self.style.SUCCESS(f'Approved sender removed: {email}{name_display}')
            )
            
        except ApprovedEmailSender.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Approved sender not found: {email}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error removing approved sender: {str(e)}')
            )

    def activate_sender(self, email):
        """Activate an approved sender"""
        try:
            sender = ApprovedEmailSender.objects.get(email_address__iexact=email)
            sender.is_active = True
            sender.save()
            
            name_display = f" ({sender.sender_name})" if sender.sender_name else ""
            self.stdout.write(
                self.style.SUCCESS(f'Approved sender activated: {email}{name_display}')
            )
            
        except ApprovedEmailSender.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Approved sender not found: {email}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error activating approved sender: {str(e)}')
            )

    def deactivate_sender(self, email):
        """Deactivate an approved sender"""
        try:
            sender = ApprovedEmailSender.objects.get(email_address__iexact=email)
            sender.is_active = False
            sender.save()
            
            name_display = f" ({sender.sender_name})" if sender.sender_name else ""
            self.stdout.write(
                self.style.SUCCESS(f'Approved sender deactivated: {email}{name_display}')
            )
            
        except ApprovedEmailSender.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Approved sender not found: {email}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error deactivating approved sender: {str(e)}')
            )
