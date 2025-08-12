from django.core.management.base import BaseCommand
from django.db import transaction
from recipe_ingestion.models import IngestionSource, IngestionJob, ExtractedRecipe
from plenary_pantry.models import Recipe


class Command(BaseCommand):
    help = 'Clean up test data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--test-only',
            action='store_true',
            help='Only delete sources marked as test data',
        )
        parser.add_argument(
            '--duplicates-only',
            action='store_true',
            help='Only clean up duplicate recipes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        test_only = options['test_only']
        duplicates_only = options['duplicates_only']

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be deleted"))

        if duplicates_only:
            self.cleanup_duplicates(dry_run)
        elif test_only:
            self.cleanup_test_sources(dry_run)
        else:
            self.cleanup_duplicates(dry_run)
            self.cleanup_test_sources(dry_run)

    def cleanup_duplicates(self, dry_run=False):
        """Clean up duplicate recipes (same name, source, and user)"""
        self.stdout.write("=== CLEANING UP DUPLICATE RECIPES ===")
        
        from collections import defaultdict
        recipe_groups = defaultdict(list)
        
        # Group by name, source_name, and created_by (the unique constraint)
        for recipe in Recipe.objects.all():
            key = (recipe.name, recipe.source_name or '', recipe.created_by_id)
            recipe_groups[key].append(recipe)
        
        total_deleted = 0
        
        for (name, source_name, user_id), recipes in recipe_groups.items():
            if len(recipes) > 1:
                source_display = f" from {source_name}" if source_name else ""
                self.stdout.write(f"\n🔄 {name}{source_display} ({len(recipes)} duplicates):")
                
                # Show all duplicates
                for recipe in recipes:
                    self.stdout.write(f"  - {recipe.id}: {recipe.created_at} ({recipe.ingredients.count()} ingredients)")
                
                # Sort by number of ingredients (keep the one with most)
                recipes.sort(key=lambda r: r.ingredients.count(), reverse=True)
                keep_recipe = recipes[0]
                
                self.stdout.write(f"  ✅ Keeping: {keep_recipe.id} ({keep_recipe.ingredients.count()} ingredients)")
                
                if not dry_run:
                    # Delete the rest
                    for recipe in recipes[1:]:
                        self.stdout.write(f"  🗑️  Deleting: {recipe.id}")
                        recipe.delete()
                        total_deleted += 1
                else:
                    total_deleted += len(recipes) - 1
        
        self.stdout.write(f"\n📊 Duplicate cleanup: {'Would delete' if dry_run else 'Deleted'} {total_deleted} duplicate recipes")

    def cleanup_test_sources(self, dry_run=False):
        """Clean up test sources"""
        self.stdout.write("\n=== CLEANING UP TEST DATA ===")
        
        # Find test sources
        test_sources = IngestionSource.objects.filter(
            source_name__icontains='test'
        ).exclude(
            source_name__icontains='production'
        )
        
        self.stdout.write(f"Found {test_sources.count()} test sources")
        
        total_deleted = 0
        
        for source in test_sources:
            self.stdout.write(f"🗑️  {'Would delete' if dry_run else 'Deleting'} test source: {source.source_name}")
            
            if not dry_run:
                # Delete associated jobs and recipes
                for job in source.jobs.all():
                    # Delete extracted recipes
                    job.extracted_recipes.all().delete()
                    # Delete the job
                    job.delete()
                
                # Delete the source
                source.delete()
            
            total_deleted += 1
        
        self.stdout.write(f"📊 Test cleanup: {'Would delete' if dry_run else 'Deleted'} {total_deleted} test sources")

    def show_summary(self):
        """Show current database state"""
        self.stdout.write(f"\n📊 Current Database State:")
        self.stdout.write(f"  - Recipes: {Recipe.objects.count()}")
        self.stdout.write(f"  - Ingestion Sources: {IngestionSource.objects.count()}")
        self.stdout.write(f"  - Ingestion Jobs: {IngestionJob.objects.count()}")
        self.stdout.write(f"  - Extracted Recipes: {ExtractedRecipe.objects.count()}")
        
        # Show test vs production breakdown
        test_sources = IngestionSource.objects.filter(source_name__icontains='test')
        prod_sources = IngestionSource.objects.exclude(source_name__icontains='test')
        
        self.stdout.write(f"\n📊 Source Breakdown:")
        self.stdout.write(f"  - Test Sources: {test_sources.count()}")
        self.stdout.write(f"  - Production Sources: {prod_sources.count()}")
        
        # Show unique recipes
        unique_recipes = Recipe.objects.values('name').distinct().count()
        self.stdout.write(f"  - Unique Recipes: {unique_recipes}")
