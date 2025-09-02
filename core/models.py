from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class Difficulty(models.Model):
    """Recipe difficulty levels"""
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name


class Cuisine(models.Model):
    """Cuisine types"""
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name


class Course(models.Model):
    """Meal courses"""
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name


class Diet(models.Model):
    """Dietary restrictions"""
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name


class Unit(models.Model):
    """Measurement units"""
    name = models.CharField(max_length=50, unique=True)
    abbreviation = models.CharField(max_length=10, blank=True)
    
    def __str__(self):
        return self.abbreviation or self.name


class Ingredient(models.Model):
    """Ingredients that can be used in recipes"""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Recipe model with all necessary fields"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructions = models.TextField()
    prep_time = models.PositiveIntegerField(help_text="Preparation time in minutes")
    cook_time = models.PositiveIntegerField(help_text="Cooking time in minutes")
    servings = models.PositiveIntegerField(default=1)
    
    # Source tracking
    source_name = models.CharField(max_length=200, blank=True, help_text="Source of the recipe (e.g., 'Better Homes and Gardens Cookbook')")
    source_url = models.URLField(blank=True, null=True, help_text="URL where recipe was found")
    source_type = models.CharField(max_length=50, blank=True, help_text="Type of source (e.g., 'cookbook', 'website', 'magazine')")
    
    # Relationships
    difficulty = models.ForeignKey(Difficulty, on_delete=models.SET_NULL, null=True, blank=True)
    cuisine = models.ForeignKey(Cuisine, on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    diet = models.ForeignKey(Diet, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['name', 'source_name', 'created_by']
    
    def __str__(self):
        if self.source_name:
            return f"{self.name} (from {self.source_name})"
        return self.name


class RecipeIngredient(models.Model):
    """Many-to-many relationship between recipes and ingredients with quantities"""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    preparation_method = models.CharField(max_length=200, blank=True, help_text="e.g., 'chopped', 'diced', 'minced'")
    optional = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['recipe', 'ingredient']
    
    def __str__(self):
        return f"{self.quantity} {self.unit} {self.ingredient.name}"


class UserProfile(models.Model):
    """Extended user profile for preferences and settings"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    household_size = models.PositiveIntegerField(default=1)
    dietary_restrictions = models.ManyToManyField(Diet, blank=True)
    preferred_cuisines = models.ManyToManyField(Cuisine, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class BlacklistedIngredient(models.Model):
    """Ingredients that users don't want to see in recipes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blacklisted_ingredients')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'ingredient']
    
    def __str__(self):
        return f"{self.user.username} - {self.ingredient.name}"


class PreferredIngredient(models.Model):
    """Ingredients that users prefer to see in recipes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='preferred_ingredients')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    preference_level = models.PositiveIntegerField(choices=[
        (1, 'Like'),
        (2, 'Really Like'),
        (3, 'Love'),
    ], default=1)
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'ingredient']
    
    def __str__(self):
        return f"{self.user.username} - {self.ingredient.name} ({self.get_preference_level_display()})"


class InventoryItem(models.Model):
    """User's current food inventory"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inventory_items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal('0'))])
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    expiration_date = models.DateField(null=True, blank=True)
    purchase_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['user', 'ingredient', 'unit']
    
    def __str__(self):
        return f"{self.quantity} {self.unit} {self.ingredient.name}"


class MenuPlan(models.Model):
    """Weekly menu planning"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='menu_plans')
    name = models.CharField(max_length=200, default="Weekly Menu")
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.start_date} to {self.end_date})"


class MenuItem(models.Model):
    """Individual meals in a menu plan"""
    menu_plan = models.ForeignKey(MenuPlan, on_delete=models.CASCADE, related_name='menu_items')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    date = models.DateField()
    meal_type = models.CharField(max_length=50, choices=[
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack'),
    ])
    servings = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['menu_plan', 'recipe', 'date', 'meal_type']
    
    def __str__(self):
        return f"{self.recipe.name} - {self.date} ({self.meal_type})"


class ShoppingList(models.Model):
    """Shopping lists generated from menu plans"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_lists')
    name = models.CharField(max_length=200, default="Shopping List")
    created_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"


class ShoppingListItem(models.Model):
    """Individual items in a shopping list"""
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    purchased = models.BooleanField(default=False)
    purchased_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.quantity} {self.unit} {self.ingredient.name}"


class RecipeRating(models.Model):
    """User ratings and reviews for recipes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipe_ratings')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'recipe']
    
    def __str__(self):
        return f"{self.user.username} - {self.recipe.name} ({self.rating}/5)"


class FavoriteRecipe(models.Model):
    """User's favorite recipes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_recipes')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'recipe']
    
    def __str__(self):
        return f"{self.user.username} - {self.recipe.name}"
