from django.contrib import admin

from recipes.models import Favorite, Ingredient, Recipe, ShoppingList, Tag

admin.site.register(Recipe)
admin.site.register(Tag)
