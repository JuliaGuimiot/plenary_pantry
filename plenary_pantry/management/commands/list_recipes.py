from django.core.management.base import BaseCommand, CommandError
from django.db.models import Prefetch
from plenary_pantry.models import Recipe, RecipeIngredient, RecipeRating, FavoriteRecipe
from django.contrib.auth.models import User
import textwrap


class Command(BaseCommand):
    help = 'Display all recipes in a human-readable format with complete metadata and directions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Filter recipes by username (optional)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of recipes to display (optional)',
        )
        parser.add_argument(
            '--include-ratings',
            action='store_true',
            help='Include user ratings and reviews',
        )
        parser.add_argument(
            '--include-favorites',
            action='store_true',
            help='Include favorite status for each user',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['detailed', 'summary', 'compact'],
            default='detailed',
            help='Output format: detailed (default), summary, or compact',
        )

    def handle(self, *args, **options):
        # Build queryset with prefetch_related for efficiency
        queryset = Recipe.objects.select_related(
            'created_by', 'difficulty', 'cuisine', 'course', 'diet'
        ).prefetch_related(
            Prefetch(
                'ingredients',
                queryset=RecipeIngredient.objects.select_related('ingredient', 'unit')
            )
        )

        # Filter by user if specified
        if options['user']:
            try:
                user = User.objects.get(username=options['user'])
                queryset = queryset.filter(created_by=user)
                self.stdout.write(f"📋 Showing recipes for user: {user.username}")
            except User.DoesNotExist:
                raise CommandError(f"User '{options['user']}' does not exist")

        # Apply limit if specified
        if options['limit']:
            queryset = queryset[:options['limit']]

        recipes = list(queryset)
        
        if not recipes:
            self.stdout.write(self.style.WARNING("No recipes found in the database."))
            return

        self.stdout.write(f"🍳 Found {len(recipes)} recipe(s) in the database")
        self.stdout.write("=" * 80)

        # Display each recipe
        for i, recipe in enumerate(recipes, 1):
            self.display_recipe(recipe, i, options)

    def display_recipe(self, recipe, index, options):
        """Display a single recipe in the specified format"""
        format_type = options['format']
        
        if format_type == 'compact':
            self.display_compact(recipe, index)
        elif format_type == 'summary':
            self.display_summary(recipe, index)
        else:  # detailed
            self.display_detailed(recipe, index, options)

    def display_compact(self, recipe, index):
        """Display recipe in compact format"""
        self.stdout.write(f"{index}. {recipe.name}")
        if recipe.source_name:
            self.stdout.write(f"   📖 Source: {recipe.source_name}")
        self.stdout.write(f"   👤 Created by: {recipe.created_by.username}")
        self.stdout.write(f"   ⏱️  Time: {recipe.prep_time}min prep + {recipe.cook_time}min cook")
        self.stdout.write(f"   👥 Serves: {recipe.servings}")
        if recipe.cuisine:
            self.stdout.write(f"   🌍 Cuisine: {recipe.cuisine.name}")
        self.stdout.write("")

    def display_summary(self, recipe, index):
        """Display recipe in summary format"""
        self.stdout.write(f"🍳 {index}. {recipe.name}")
        self.stdout.write("-" * 60)
        
        # Basic info
        self.stdout.write(f"📖 Source: {recipe.source_name or 'Unknown'}")
        if recipe.source_url:
            self.stdout.write(f"🔗 URL: {recipe.source_url}")
        self.stdout.write(f"👤 Created by: {recipe.created_by.username}")
        self.stdout.write(f"📅 Created: {recipe.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        # Timing and servings
        total_time = recipe.prep_time + recipe.cook_time
        self.stdout.write(f"⏱️  Prep: {recipe.prep_time}min | Cook: {recipe.cook_time}min | Total: {total_time}min")
        self.stdout.write(f"👥 Serves: {recipe.servings}")
        
        # Categories
        categories = []
        if recipe.difficulty:
            categories.append(f"Difficulty: {recipe.difficulty.name}")
        if recipe.cuisine:
            categories.append(f"Cuisine: {recipe.cuisine.name}")
        if recipe.course:
            categories.append(f"Course: {recipe.course.name}")
        if recipe.diet:
            categories.append(f"Diet: {recipe.diet.name}")
        
        if categories:
            self.stdout.write(f"🏷️  {' | '.join(categories)}")
        
        # Description
        if recipe.description:
            self.stdout.write(f"📝 Description: {recipe.description}")
        
        # Ingredients count
        ingredient_count = recipe.ingredients.count()
        self.stdout.write(f"🥘 Ingredients: {ingredient_count} items")
        
        self.stdout.write("")

    def display_detailed(self, recipe, index, options):
        """Display recipe in detailed format"""
        self.stdout.write(f"🍳 {index}. {recipe.name}")
        self.stdout.write("=" * 80)
        
        # Header information
        self.stdout.write(f"📖 Source: {recipe.source_name or 'Unknown'}")
        if recipe.source_type:
            self.stdout.write(f"📚 Source Type: {recipe.source_type}")
        if recipe.source_url:
            self.stdout.write(f"🔗 URL: {recipe.source_url}")
        
        self.stdout.write(f"👤 Created by: {recipe.created_by.username}")
        self.stdout.write(f"📅 Created: {recipe.created_at.strftime('%Y-%m-%d %H:%M')}")
        self.stdout.write(f"🔄 Updated: {recipe.updated_at.strftime('%Y-%m-%d %H:%M')}")
        self.stdout.write(f"🌐 Public: {'Yes' if recipe.is_public else 'No'}")
        
        # Timing and servings
        total_time = recipe.prep_time + recipe.cook_time
        self.stdout.write(f"⏱️  Preparation Time: {recipe.prep_time} minutes")
        self.stdout.write(f"🔥 Cooking Time: {recipe.cook_time} minutes")
        self.stdout.write(f"⏰ Total Time: {total_time} minutes")
        self.stdout.write(f"👥 Servings: {recipe.servings}")
        
        # Categories
        self.stdout.write("\n🏷️  CATEGORIES:")
        if recipe.difficulty:
            self.stdout.write(f"   Difficulty: {recipe.difficulty.name}")
        else:
            self.stdout.write("   Difficulty: Not specified")
            
        if recipe.cuisine:
            self.stdout.write(f"   Cuisine: {recipe.cuisine.name}")
        else:
            self.stdout.write("   Cuisine: Not specified")
            
        if recipe.course:
            self.stdout.write(f"   Course: {recipe.course.name}")
        else:
            self.stdout.write("   Course: Not specified")
            
        if recipe.diet:
            self.stdout.write(f"   Diet: {recipe.diet.name}")
        else:
            self.stdout.write("   Diet: Not specified")
        
        # Description
        if recipe.description:
            self.stdout.write(f"\n📝 DESCRIPTION:")
            wrapped_desc = textwrap.fill(recipe.description, width=70, initial_indent="   ", subsequent_indent="   ")
            self.stdout.write(wrapped_desc)
        
        # Ingredients
        self.stdout.write(f"\n🥘 INGREDIENTS ({recipe.ingredients.count()} items):")
        if recipe.ingredients.exists():
            for ri in recipe.ingredients.all():
                ingredient_text = f"   • {ri.quantity} {ri.unit} {ri.ingredient.name}"
                if ri.preparation_method:
                    ingredient_text += f" ({ri.preparation_method})"
                if ri.optional:
                    ingredient_text += " [optional]"
                self.stdout.write(ingredient_text)
        else:
            self.stdout.write("   No ingredients listed")
        
        # Instructions
        self.stdout.write(f"\n👨‍🍳 INSTRUCTIONS:")
        wrapped_instructions = textwrap.fill(recipe.instructions, width=70, initial_indent="   ", subsequent_indent="   ")
        self.stdout.write(wrapped_instructions)
        
        # Ratings and reviews (if requested)
        if options['include_ratings']:
            self.display_ratings(recipe)
        
        # Favorites (if requested)
        if options['include_favorites']:
            self.display_favorites(recipe)
        
        self.stdout.write("\n" + "=" * 80 + "\n")

    def display_ratings(self, recipe):
        """Display ratings and reviews for the recipe"""
        ratings = recipe.ratings.all().order_by('-created_at')
        if ratings.exists():
            self.stdout.write(f"\n⭐ RATINGS & REVIEWS ({ratings.count()}):")
            for rating in ratings:
                stars = "⭐" * rating.rating
                self.stdout.write(f"   {stars} ({rating.rating}/5) by {rating.user.username}")
                if rating.review:
                    wrapped_review = textwrap.fill(rating.review, width=65, initial_indent="      ", subsequent_indent="      ")
                    self.stdout.write(wrapped_review)
                self.stdout.write(f"      📅 {rating.created_at.strftime('%Y-%m-%d')}")
        else:
            self.stdout.write(f"\n⭐ RATINGS & REVIEWS: No ratings yet")

    def display_favorites(self, recipe):
        """Display users who favorited this recipe"""
        favorites = recipe.favorited_by.all()
        if favorites.exists():
            usernames = [fav.user.username for fav in favorites]
            self.stdout.write(f"\n❤️  FAVORITED BY: {', '.join(usernames)}")
        else:
            self.stdout.write(f"\n❤️  FAVORITED BY: No favorites yet")
