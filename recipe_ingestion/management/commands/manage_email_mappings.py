from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from recipe_ingestion.models import UserEmailMapping


class Command(BaseCommand):
    help = 'Manage user email mappings for recipe ingestion'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all email mappings',
        )
        parser.add_argument(
            '--add',
            type=str,
            help='Add email mapping (format: username:email@domain.com)',
        )
        parser.add_argument(
            '--remove',
            type=str,
            help='Remove email mapping by email address',
        )
        parser.add_argument(
            '--activate',
            type=str,
            help='Activate email mapping by email address',
        )
        parser.add_argument(
            '--deactivate',
            type=str,
            help='Deactivate email mapping by email address',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_mappings()
        elif options['add']:
            self.add_mapping(options['add'])
        elif options['remove']:
            self.remove_mapping(options['remove'])
        elif options['activate']:
            self.activate_mapping(options['activate'])
        elif options['deactivate']:
            self.deactivate_mapping(options['deactivate'])
        else:
            self.stdout.write(
                self.style.ERROR('Please specify an action: --list, --add, --remove, --activate, or --deactivate')
            )

    def list_mappings(self):
        """List all email mappings"""
        mappings = UserEmailMapping.objects.all().order_by('user__username', 'email_address')
        
        if not mappings:
            self.stdout.write(self.style.WARNING('No email mappings found'))
            return
        
        self.stdout.write(self.style.SUCCESS('Email Mappings:'))
        self.stdout.write('-' * 80)
        
        for mapping in mappings:
            status = 'ACTIVE' if mapping.is_active else 'INACTIVE'
            self.stdout.write(
                f"{mapping.user.username:<20} | {mapping.email_address:<30} | {status:<8} | {mapping.created_at.strftime('%Y-%m-%d %H:%M')}"
            )

    def add_mapping(self, mapping_str):
        """Add a new email mapping"""
        try:
            username, email = mapping_str.split(':', 1)
            username = username.strip()
            email = email.strip()
            
            # Validate username
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{username}" not found')
                )
                return
            
            # Check if email already exists
            if UserEmailMapping.objects.filter(email_address__iexact=email).exists():
                self.stdout.write(
                    self.style.ERROR(f'Email "{email}" is already mapped to a user')
                )
                return
            
            # Create mapping
            mapping = UserEmailMapping.objects.create(
                user=user,
                email_address=email
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Email mapping created: {user.username} -> {email}'
                )
            )
            
        except ValueError:
            self.stdout.write(
                self.style.ERROR('Invalid format. Use: username:email@domain.com')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating mapping: {str(e)}')
            )

    def remove_mapping(self, email):
        """Remove an email mapping"""
        try:
            mapping = UserEmailMapping.objects.get(email_address__iexact=email)
            username = mapping.user.username
            mapping.delete()
            
            self.stdout.write(
                self.style.SUCCESS(f'Email mapping removed: {username} -> {email}')
            )
            
        except UserEmailMapping.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Email mapping not found: {email}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error removing mapping: {str(e)}')
            )

    def activate_mapping(self, email):
        """Activate an email mapping"""
        try:
            mapping = UserEmailMapping.objects.get(email_address__iexact=email)
            mapping.is_active = True
            mapping.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Email mapping activated: {mapping.user.username} -> {email}')
            )
            
        except UserEmailMapping.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Email mapping not found: {email}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error activating mapping: {str(e)}')
            )

    def deactivate_mapping(self, email):
        """Deactivate an email mapping"""
        try:
            mapping = UserEmailMapping.objects.get(email_address__iexact=email)
            mapping.is_active = False
            mapping.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Email mapping deactivated: {mapping.user.username} -> {email}')
            )
            
        except UserEmailMapping.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Email mapping not found: {email}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error deactivating mapping: {str(e)}')
            )
