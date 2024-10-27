from django.contrib import admin

from recipes.constants import ADMIN_EXTRA_FIELDS, ADMIN_MIN_NUM
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Tag)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = ADMIN_EXTRA_FIELDS
    min_num = ADMIN_MIN_NUM


class RecipeTagInline(admin.TabularInline):
    model = Recipe.tags.through
    extra = ADMIN_EXTRA_FIELDS
    min_num = ADMIN_MIN_NUM


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    list_editable = ('user', 'recipe')


class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'measurement_unit',
    )
    list_editable = ('measurement_unit',)
    list_display_links = ('name',)
    search_fields = ('name', )
    list_filter = ('measurement_unit',)
    empty_value_display = 'Не задано'


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'author',
    )
    list_display_links = ('name',)
    search_fields = ('name', 'author__username',)
    list_filter = ('tags',)
    readonly_fields = ('recipe_in_favorites', )
    inlines = (RecipeIngredientInline, RecipeTagInline)

    @admin.display(description='Добавлено в избранное раз')
    def recipe_in_favorites(self, obj):
        return obj.favorites.count()


class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount',)
    list_editable = ('amount',)


class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe',)
    list_editable = ('recipe',)
    list_display_links = ('user',)


class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug',)
    list_editable = ('name', 'slug',)
    search_fields = ('name',)


admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(RecipeIngredient, RecipeIngredientAdmin)
admin.site.register(ShoppingList, ShoppingListAdmin)
admin.site.register(Tag, TagAdmin)
