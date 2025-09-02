from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Prefetch
from core.models import Ingredient, Unit, RecipeIngredient
from recipe_ingestion.models import IngredientMapping
import textwrap


class Command(BaseCommand):
    help = 'Display all ingredients in a human-readable format with usage statistics and mappings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of ingredients to display (optional)',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['detailed', 'summary', 'compact', 'mappings'],
            default='summary',
            help='Output format: detailed, summary, compact, or mappings (default: summary)',
        )
        parser.add_argument(
            '--search',
            type=str,
            help='Search for ingredients containing this text (case-insensitive)',
        )
        parser.add_argument(
            '--include-usage',
            action='store_true',
            help='Include usage statistics (how many recipes use each ingredient)',
        )
        parser.add_argument(
            '--include-mappings',
            action='store_true',
            help='Include ingredient mappings from recipe ingestion',
        )
        parser.add_argument(
            '--sort-by',
            type=str,
            choices=['name', 'created', 'usage', 'mappings'],
            default='name',
            help='Sort ingredients by: name (default), created, usage, or mappings',
        )

    def handle(self, *args, **options):
        # Build queryset with prefetch_related for efficiency
        queryset = Ingredient.objects.all()

        # Apply search filter if provided
        if options['search']:
            queryset = queryset.filter(name__icontains=options['search'])

        # Add usage statistics if requested
        if options['include_usage'] or options['sort_by'] == 'usage':
            queryset = queryset.annotate(
                recipe_count=Count('recipeingredient', distinct=True)
            )

        # Add mapping statistics if requested
        if options['include_mappings'] or options['sort_by'] == 'mappings':
            queryset = queryset.annotate(
                mapping_count=Count('ingredientmapping', distinct=True)
            )

        # Apply sorting
        if options['sort_by'] == 'name':
            queryset = queryset.order_by('name')
        elif options['sort_by'] == 'created':
            queryset = queryset.order_by('-created_at')
        elif options['sort_by'] == 'usage':
            queryset = queryset.order_by('-recipe_count')
        elif options['sort_by'] == 'mappings':
            queryset = queryset.order_by('-mapping_count')

        # Apply limit if specified
        if options['limit']:
            queryset = queryset[:options['limit']]

        ingredients = list(queryset)
        
        if not ingredients:
            search_msg = f" matching '{options['search']}'" if options['search'] else ""
            self.stdout.write(self.style.WARNING(f"No ingredients found{search_msg} in the database."))
            return

        # Display header
        search_msg = f" matching '{options['search']}'" if options['search'] else ""
        self.stdout.write(f"🥘 Found {len(ingredients)} ingredient(s){search_msg} in the database")
        self.stdout.write("=" * 80)

        # Display each ingredient
        for i, ingredient in enumerate(ingredients, 1):
            self.display_ingredient(ingredient, i, options)

    def display_ingredient(self, ingredient, index, options):
        """Display a single ingredient in the specified format"""
        format_type = options['format']
        
        if format_type == 'compact':
            self.display_compact(ingredient, index, options)
        elif format_type == 'mappings':
            self.display_mappings(ingredient, index, options)
        elif format_type == 'detailed':
            self.display_detailed(ingredient, index, options)
        else:  # summary
            self.display_summary(ingredient, index, options)

    def display_compact(self, ingredient, index, options):
        """Display ingredient in compact format"""
        self.stdout.write(f"{index}. {ingredient.name}")
        if hasattr(ingredient, 'recipe_count') and ingredient.recipe_count > 0:
            self.stdout.write(f"   📊 Used in {ingredient.recipe_count} recipe(s)")
        if hasattr(ingredient, 'mapping_count') and ingredient.mapping_count > 0:
            self.stdout.write(f"   🔗 {ingredient.mapping_count} mapping(s)")
        self.stdout.write("")

    def display_summary(self, ingredient, index, options):
        """Display ingredient in summary format"""
        self.stdout.write(f"🥘 {index}. {ingredient.name}")
        self.stdout.write("-" * 60)
        
        # Basic info
        self.stdout.write(f"📅 Created: {ingredient.created_at.strftime('%Y-%m-%d %H:%M')}")
        self.stdout.write(f"🔄 Updated: {ingredient.updated_at.strftime('%Y-%m-%d %H:%M')}")
        
        # Usage statistics
        if hasattr(ingredient, 'recipe_count'):
            self.stdout.write(f"📊 Used in {ingredient.recipe_count} recipe(s)")
        
        # Mapping statistics
        if hasattr(ingredient, 'mapping_count'):
            self.stdout.write(f"🔗 {ingredient.mapping_count} mapping(s) from recipe ingestion")
        
        # Description
        if ingredient.description:
            wrapped_desc = textwrap.fill(ingredient.description, width=70, initial_indent="📝 ", subsequent_indent="   ")
            self.stdout.write(wrapped_desc)
        else:
            self.stdout.write("📝 No description available")
        
        self.stdout.write("")

    def display_detailed(self, ingredient, index, options):
        """Display ingredient in detailed format"""
        self.stdout.write(f"🥘 {index}. {ingredient.name}")
        self.stdout.write("=" * 80)
        
        # Basic information
        self.stdout.write(f"📅 Created: {ingredient.created_at.strftime('%Y-%m-%d %H:%M')}")
        self.stdout.write(f"🔄 Updated: {ingredient.updated_at.strftime('%Y-%m-%d %H:%M')}")
        
        # Usage statistics
        if hasattr(ingredient, 'recipe_count'):
            self.stdout.write(f"📊 Used in {ingredient.recipe_count} recipe(s)")
            
            # Show recent recipe usage
            if ingredient.recipe_count > 0:
                recent_recipes = RecipeIngredient.objects.filter(
                    ingredient=ingredient
                ).select_related('recipe', 'unit')[:5]
                
                self.stdout.write(f"\n📋 Recent recipe usage:")
                for ri in recent_recipes:
                    self.stdout.write(f"   • {ri.quantity} {ri.unit} in '{ri.recipe.name}'")
                    if ri.preparation_method:
                        self.stdout.write(f"     (preparation: {ri.preparation_method})")
                    if ri.optional:
                        self.stdout.write(f"     [optional]")
        
        # Mapping statistics
        if hasattr(ingredient, 'mapping_count'):
            self.stdout.write(f"\n🔗 {ingredient.mapping_count} mapping(s) from recipe ingestion")
            
            # Show recent mappings
            if ingredient.mapping_count > 0:
                recent_mappings = IngredientMapping.objects.filter(
                    normalized_ingredient=ingredient
                ).order_by('-created_at')[:5]
                
                self.stdout.write(f"\n📝 Recent mappings:")
                for mapping in recent_mappings:
                    self.stdout.write(f"   • '{mapping.raw_text}' -> {ingredient.name}")
                    if mapping.confidence > 0:
                        self.stdout.write(f"     (confidence: {mapping.confidence:.2f})")
        
        # Description
        if ingredient.description:
            self.stdout.write(f"\n📝 DESCRIPTION:")
            wrapped_desc = textwrap.fill(ingredient.description, width=70, initial_indent="   ", subsequent_indent="   ")
            self.stdout.write(wrapped_desc)
        else:
            self.stdout.write(f"\n📝 DESCRIPTION: No description available")
        
        self.stdout.write("\n" + "=" * 80 + "\n")

    def display_mappings(self, ingredient, index, options):
        """Display ingredient with focus on mappings"""
        self.stdout.write(f"🔗 {index}. {ingredient.name}")
        self.stdout.write("-" * 60)
        
        # Get all mappings for this ingredient
        mappings = IngredientMapping.objects.filter(
            normalized_ingredient=ingredient
        ).order_by('-confidence', '-created_at')
        
        if mappings.exists():
            self.stdout.write(f"📝 {mappings.count()} mapping(s) found:")
            for mapping in mappings:
                confidence_str = f" (confidence: {mapping.confidence:.2f})" if mapping.confidence > 0 else ""
                self.stdout.write(f"   • '{mapping.raw_text}'{confidence_str}")
                if mapping.quantity and mapping.unit:
                    self.stdout.write(f"     Quantity: {mapping.quantity} {mapping.unit}")
                if mapping.preparation_method:
                    self.stdout.write(f"     Preparation: {mapping.preparation_method}")
                self.stdout.write(f"     Created: {mapping.created_at.strftime('%Y-%m-%d %H:%M')}")
                self.stdout.write("")
        else:
            self.stdout.write("📝 No mappings found for this ingredient")
        
        self.stdout.write("")

