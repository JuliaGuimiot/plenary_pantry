from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from recipe_ingestion.models import IngestionSource
from recipe_ingestion.services import RecipeIngestionService


class Command(BaseCommand):
    help = 'Test the recipe ingestion system with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username to create test data for'
        )

    def handle(self, *args, **options):
        username = options['username']
        
        # Get or create user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Created user: {username} (password: password123)')
            )
        
        # Test recipe text
        test_recipe = """
        Chocolate Chip Cookies
        
        Ingredients:
        2 1/4 cups all-purpose flour
        1 cup butter, softened
        3/4 cup granulated sugar
        3/4 cup brown sugar
        2 large eggs
        1 tsp vanilla extract
        1 tsp baking soda
        1/2 tsp salt
        2 cups chocolate chips
        
        Instructions:
        1. Preheat oven to 375°F (190°C).
        2. In a large bowl, cream together butter, granulated sugar, and brown sugar until smooth.
        3. Beat in eggs one at a time, then stir in vanilla.
        4. In a separate bowl, combine flour, baking soda, and salt.
        5. Gradually blend the flour mixture into the butter mixture.
        6. Stir in chocolate chips.
        7. Drop rounded tablespoons of dough onto ungreased baking sheets.
        8. Bake for 9 to 11 minutes or until golden brown.
        9. Cool on baking sheets for 2 minutes, then remove to wire racks.
        
        Prep time: 15 minutes
        Cook time: 10 minutes
        Serves: 24 cookies
        """
        
        # Create ingestion source
        source = IngestionSource.objects.create(
            user=user,
            source_type='text',
            source_name='Test Chocolate Chip Cookies',
            raw_text=test_recipe
        )
        
        self.stdout.write('Created test ingestion source...')
        
        # Process the source
        service = RecipeIngestionService(user)
        job = service.process_source(source)
        
        self.stdout.write(
            self.style.SUCCESS(f'Processing completed! Job ID: {job.id}')
        )
        self.stdout.write(f'Status: {job.status}')
        self.stdout.write(f'Recipes found: {job.recipes_found}')
        self.stdout.write(f'Recipes processed: {job.recipes_processed}')
        
        # Show extracted recipes
        for recipe in job.extracted_recipes.all():
            self.stdout.write(f'\nExtracted Recipe: {recipe.raw_name}')
            self.stdout.write(f'Confidence: {recipe.confidence_score:.2f}')
            self.stdout.write(f'Ingredients: {len(recipe.raw_ingredients)}')
            self.stdout.write(f'Instructions length: {len(recipe.raw_instructions)} characters')
        
        # Normalize and save recipes
        if job.extracted_recipes.exists():
            self.stdout.write('\nNormalizing and saving recipes...')
            saved_recipes = service.normalize_and_save_recipes(job)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully saved {len(saved_recipes)} recipes!')
            )
            
            for recipe in saved_recipes:
                self.stdout.write(f'- {recipe.name} ({recipe.ingredients.count()} ingredients)')
        
        self.stdout.write(
            self.style.SUCCESS('\nTest completed successfully!')
        )
