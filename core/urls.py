from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard and main views
    path('', views.dashboard, name='dashboard'),
    
    # Recipe management
    path('recipes/', views.recipe_list, name='recipe_list'),
    path('recipes/<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('recipes/<int:recipe_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('recipes/<int:recipe_id>/rate/', views.rate_recipe, name='rate_recipe'),
    
    # Public recipes
    path('public-recipes/', views.public_recipes, name='public_recipes'),
    
    # Ingredient management
    path('ingredients/', views.ingredient_list, name='ingredient_list'),
    
    # Pantry management
    path('pantry/', views.pantry_view, name='pantry'),
    
    # Menu planning
    path('menu/', views.menu_planning, name='menu_planning'),
    
    # Shopping lists
    path('shopping/', views.shopping_lists, name='shopping_lists'),
]
