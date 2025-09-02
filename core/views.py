from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    Recipe, Ingredient, Unit, Difficulty, Cuisine, Course, Diet,
    RecipeIngredient, InventoryItem, MenuPlan, MenuItem, ShoppingList,
    ShoppingListItem, RecipeRating, FavoriteRecipe
)


@login_required
def dashboard(request):
    """Main dashboard for the core app"""
    user = request.user
    
    # Get user's recipes
    user_recipes = Recipe.objects.filter(created_by=user).order_by('-created_at')[:5]
    total_recipes = Recipe.objects.filter(created_by=user).count()
    
    # Get recent favorites
    recent_favorites = FavoriteRecipe.objects.filter(user=user).select_related('recipe').order_by('-created_at')[:5]
    
    # Get pantry items
    pantry_items = InventoryItem.objects.filter(user=user).select_related('ingredient', 'unit').order_by('expiration_date')[:10]
    expiring_soon = InventoryItem.objects.filter(
        user=user,
        expiration_date__lte=timezone.now().date() + timedelta(days=7),
        expiration_date__gte=timezone.now().date()
    ).count()
    
    # Get current menu plan
    current_menu = MenuPlan.objects.filter(
        user=user,
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    ).first()
    
    # Get shopping lists
    active_shopping_lists = ShoppingList.objects.filter(user=user, completed=False).order_by('-created_at')[:3]
    
    context = {
        'user_recipes': user_recipes,
        'total_recipes': total_recipes,
        'recent_favorites': recent_favorites,
        'pantry_items': pantry_items,
        'expiring_soon': expiring_soon,
        'current_menu': current_menu,
        'active_shopping_lists': active_shopping_lists,
    }
    
    return render(request, 'core/dashboard.html', context)


@login_required
def recipe_list(request):
    """Display list of user's recipes with filtering and search"""
    user = request.user
    
    # Get filter parameters
    search_query = request.GET.get('q', '')
    difficulty = request.GET.get('difficulty', '')
    cuisine = request.GET.get('cuisine', '')
    course = request.GET.get('course', '')
    diet = request.GET.get('diet', '')
    
    # Start with user's recipes
    recipes = Recipe.objects.filter(created_by=user)
    
    # Apply filters
    if search_query:
        recipes = recipes.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(instructions__icontains=search_query)
        )
    
    if difficulty:
        recipes = recipes.filter(difficulty__name=difficulty)
    
    if cuisine:
        recipes = recipes.filter(cuisine__name=cuisine)
    
    if course:
        recipes = recipes.filter(course__name=course)
    
    if diet:
        recipes = recipes.filter(diet__name=diet)
    
    # Get filter options for the form
    difficulties = Difficulty.objects.all().order_by('name')
    cuisines = Cuisine.objects.all().order_by('name')
    courses = Course.objects.all().order_by('name')
    diets = Diet.objects.all().order_by('name')
    
    # Pagination
    paginator = Paginator(recipes.order_by('-created_at'), 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'difficulty': difficulty,
        'cuisine': cuisine,
        'course': course,
        'diet': diet,
        'difficulties': difficulties,
        'cuisines': cuisines,
        'courses': courses,
        'diets': diets,
    }
    
    return render(request, 'core/recipe_list.html', context)


@login_required
def recipe_detail(request, recipe_id):
    """Display detailed view of a recipe"""
    user = request.user
    recipe = get_object_or_404(Recipe, id=recipe_id, created_by=user)
    
    # Get recipe ingredients with quantities
    ingredients = RecipeIngredient.objects.filter(recipe=recipe).select_related('ingredient', 'unit')
    
    # Check if recipe is favorited by user
    is_favorited = FavoriteRecipe.objects.filter(user=user, recipe=recipe).exists()
    
    # Get user's rating if exists
    user_rating = RecipeRating.objects.filter(user=user, recipe=recipe).first()
    
    # Get average rating
    avg_rating = RecipeRating.objects.filter(recipe=recipe).aggregate(avg=Avg('rating'))['avg'] or 0
    
    context = {
        'recipe': recipe,
        'ingredients': ingredients,
        'is_favorited': is_favorited,
        'user_rating': user_rating,
        'avg_rating': round(avg_rating, 1),
    }
    
    return render(request, 'core/recipe_detail.html', context)


@login_required
def ingredient_list(request):
    """Display list of ingredients with search and filtering"""
    user = request.user
    
    search_query = request.GET.get('q', '')
    
    # Get ingredients used in user's recipes
    user_ingredients = Ingredient.objects.filter(
        recipeingredient__recipe__created_by=user
    ).distinct()
    
    if search_query:
        user_ingredients = user_ingredients.filter(name__icontains=search_query)
    
    # Pagination
    paginator = Paginator(user_ingredients.order_by('name'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'core/ingredient_list.html', context)


@login_required
def pantry_view(request):
    """Display user's pantry items"""
    user = request.user
    
    # Get pantry items
    pantry_items = InventoryItem.objects.filter(user=user).select_related('ingredient', 'unit')
    
    # Group by expiration status
    expired = pantry_items.filter(expiration_date__lt=timezone.now().date())
    expiring_soon = pantry_items.filter(
        expiration_date__lte=timezone.now().date() + timedelta(days=7),
        expiration_date__gte=timezone.now().date()
    )
    good = pantry_items.filter(
        Q(expiration_date__gt=timezone.now().date() + timedelta(days=7)) |
        Q(expiration_date__isnull=True)
    )
    
    context = {
        'expired_items': expired,
        'expiring_soon_items': expiring_soon,
        'good_items': good,
    }
    
    return render(request, 'core/pantry.html', context)


@login_required
def menu_planning(request):
    """Display and manage menu plans"""
    user = request.user
    
    # Get current and upcoming menu plans
    current_date = timezone.now().date()
    current_menus = MenuPlan.objects.filter(
        user=user,
        start_date__lte=current_date,
        end_date__gte=current_date
    )
    
    upcoming_menus = MenuPlan.objects.filter(
        user=user,
        start_date__gt=current_date
    ).order_by('start_date')[:5]
    
    # Get today's menu items
    today_items = MenuItem.objects.filter(
        menu_plan__user=user,
        date=current_date
    ).select_related('recipe', 'menu_plan').order_by('meal_type')
    
    context = {
        'current_menus': current_menus,
        'upcoming_menus': upcoming_menus,
        'today_items': today_items,
        'current_date': current_date,
    }
    
    return render(request, 'core/menu_planning.html', context)


@login_required
def shopping_lists(request):
    """Display and manage shopping lists"""
    user = request.user
    
    # Get active and completed shopping lists
    active_lists = ShoppingList.objects.filter(user=user, completed=False).order_by('-created_at')
    completed_lists = ShoppingList.objects.filter(user=user, completed=True).order_by('-completed_at')[:10]
    
    context = {
        'active_lists': active_lists,
        'completed_lists': completed_lists,
    }
    
    return render(request, 'core/shopping_lists.html', context)


@login_required
@require_http_methods(["POST"])
def toggle_favorite(request, recipe_id):
    """Toggle favorite status of a recipe"""
    user = request.user
    recipe = get_object_or_404(Recipe, id=recipe_id, created_by=user)
    
    favorite, created = FavoriteRecipe.objects.get_or_create(user=user, recipe=recipe)
    
    if not created:
        favorite.delete()
        is_favorited = False
        messages.success(request, f'"{recipe.name}" removed from favorites')
    else:
        is_favorited = True
        messages.success(request, f'"{recipe.name}" added to favorites')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'is_favorited': is_favorited})
    
    return redirect('recipe_detail', recipe_id=recipe_id)


@login_required
@require_http_methods(["POST"])
def rate_recipe(request, recipe_id):
    """Rate a recipe"""
    user = request.user
    recipe = get_object_or_404(Recipe, id=recipe_id, created_by=user)
    
    rating_value = request.POST.get('rating')
    review_text = request.POST.get('review', '')
    
    if not rating_value:
        messages.error(request, 'Please provide a rating')
        return redirect('recipe_detail', recipe_id=recipe_id)
    
    try:
        rating_value = int(rating_value)
        if rating_value < 1 or rating_value > 5:
            raise ValueError()
    except ValueError:
        messages.error(request, 'Invalid rating value')
        return redirect('recipe_detail', recipe_id=recipe_id)
    
    # Update or create rating
    rating, created = RecipeRating.objects.update_or_create(
        user=user,
        recipe=recipe,
        defaults={
            'rating': rating_value,
            'review': review_text
        }
    )
    
    if created:
        messages.success(request, f'Rating added for "{recipe.name}"')
    else:
        messages.success(request, f'Rating updated for "{recipe.name}"')
    
    return redirect('recipe_detail', recipe_id=recipe_id)


@login_required
def public_recipes(request):
    """Display public recipes from all users"""
    search_query = request.GET.get('q', '')
    cuisine = request.GET.get('cuisine', '')
    difficulty = request.GET.get('difficulty', '')
    
    # Get public recipes
    recipes = Recipe.objects.filter(is_public=True)
    
    # Apply filters
    if search_query:
        recipes = recipes.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if cuisine:
        recipes = recipes.filter(cuisine__name=cuisine)
    
    if difficulty:
        recipes = recipes.filter(difficulty__name=difficulty)
    
    # Get filter options
    cuisines = Cuisine.objects.all().order_by('name')
    difficulties = Difficulty.objects.all().order_by('name')
    
    # Pagination
    paginator = Paginator(recipes.order_by('-created_at'), 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'cuisine': cuisine,
        'difficulty': difficulty,
        'cuisines': cuisines,
        'difficulties': difficulties,
    }
    
    return render(request, 'core/public_recipes.html', context)
