from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Difficulty, Cuisine, Course, Diet, Unit, Ingredient, Recipe, 
    RecipeIngredient, InventoryItem, MenuPlan, MenuItem, ShoppingList, 
    ShoppingListItem, RecipeRating, FavoriteRecipe
)


@admin.register(Difficulty)
class DifficultyAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Cuisine)
class CuisineAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Diet)
class DietAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'abbreviation']
    search_fields = ['name', 'abbreviation']
    ordering = ['name']


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    date_hierarchy = 'created_at'


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ['ingredient', 'unit']


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'created_by', 'difficulty', 'cuisine', 'course', 
        'prep_time', 'cook_time', 'servings', 'is_public', 'created_at'
    ]
    list_filter = [
        'difficulty', 'cuisine', 'course', 'diet', 'is_public', 
        'created_at', 'updated_at'
    ]
    search_fields = ['name', 'description', 'instructions', 'source_name', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['difficulty', 'cuisine', 'course', 'diet', 'created_by']
    filter_horizontal = []
    inlines = [RecipeIngredientInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'instructions', 'prep_time', 'cook_time', 'servings')
        }),
        ('Categorization', {
            'fields': ('difficulty', 'cuisine', 'course', 'diet')
        }),
        ('Source Information', {
            'fields': ('source_name', 'source_url', 'source_type'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'is_public', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ['recipe', 'ingredient', 'quantity', 'unit', 'preparation_method']
    list_filter = ['unit', 'preparation_method']
    search_fields = ['recipe__name', 'ingredient__name', 'preparation_method']
    autocomplete_fields = ['recipe', 'ingredient', 'unit']
    ordering = ['recipe__name', 'ingredient__name']


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'ingredient', 'quantity', 'unit', 'expiration_date', 
        'purchase_date', 'notes'
    ]
    list_filter = ['expiration_date', 'purchase_date', 'unit']
    search_fields = ['user__username', 'ingredient__name', 'notes']
    autocomplete_fields = ['user', 'ingredient', 'unit']
    date_hierarchy = 'purchase_date'
    ordering = ['-purchase_date']


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1
    autocomplete_fields = ['recipe']


@admin.register(MenuPlan)
class MenuPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user', 'start_date', 'end_date', 'created_at', 
        'menu_items_count'
    ]
    list_filter = ['start_date', 'end_date', 'created_at']
    search_fields = ['name', 'user__username']
    autocomplete_fields = ['user']
    inlines = [MenuItemInline]
    date_hierarchy = 'start_date'
    ordering = ['-start_date']
    
    def menu_items_count(self, obj):
        return obj.menu_items.count()
    menu_items_count.short_description = 'Menu Items'


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = [
        'menu_plan', 'recipe', 'date', 'meal_type', 'servings', 'notes'
    ]
    list_filter = ['meal_type', 'date', 'servings']
    search_fields = ['menu_plan__name', 'recipe__name', 'notes']
    autocomplete_fields = ['menu_plan', 'recipe']
    date_hierarchy = 'date'
    ordering = ['-date', 'meal_type']


class ShoppingListItemInline(admin.TabularInline):
    model = ShoppingListItem
    extra = 1
    autocomplete_fields = ['ingredient', 'unit']


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user', 'created_at', 'completed', 'completed_at', 
        'items_count'
    ]
    list_filter = ['completed', 'created_at', 'completed_at']
    search_fields = ['name', 'user__username']
    autocomplete_fields = ['user']
    inlines = [ShoppingListItemInline]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Items'


@admin.register(ShoppingListItem)
class ShoppingListItemAdmin(admin.ModelAdmin):
    list_display = [
        'shopping_list', 'ingredient', 'quantity', 'unit', 
        'purchased', 'purchased_at'
    ]
    list_filter = ['purchased', 'purchased_at', 'unit']
    search_fields = ['shopping_list__name', 'ingredient__name', 'notes']
    autocomplete_fields = ['shopping_list', 'ingredient', 'unit']
    date_hierarchy = 'purchased_at'
    ordering = ['shopping_list__name', 'ingredient__name']


@admin.register(RecipeRating)
class RecipeRatingAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'recipe', 'rating', 'created_at', 'updated_at'
    ]
    list_filter = ['rating', 'created_at', 'updated_at']
    search_fields = ['user__username', 'recipe__name', 'review']
    autocomplete_fields = ['user', 'recipe']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ['user', 'recipe', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'recipe__name']
    autocomplete_fields = ['user', 'recipe']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
