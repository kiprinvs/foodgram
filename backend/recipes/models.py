import random
import string

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import UniqueConstraint

from api.constants import (MAX_LENGTH_INGREDIENT_NAME,
                           MAX_LENGTH_MEASUREMENT_UNIT, MAX_LENGTH_RECIPE_NAME,
                           MAX_LENGTH_SHORT_LINK, MAX_LENGTH_TAG)
from recipes.constants import (MAX_AMOUNT, MAX_COOKING_TIME, MIN_AMOUNT,
                               MIN_COOKING_TIME)

User = get_user_model()


class Recipe(models.Model):
    """Модель рецепта."""

    name = models.CharField(
        verbose_name='Название',
        max_length=MAX_LENGTH_RECIPE_NAME
    )
    description = models.TextField(
        verbose_name='Описание',
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления(в минутах)',
        validators=[
            MinValueValidator(
                MIN_COOKING_TIME,
                message='Время приготовления должно быть не менее '
                f'{MIN_COOKING_TIME} минуты.'
            ),
            MaxValueValidator(
                MAX_COOKING_TIME,
                message='Время приготовления не должно превышать '
                f'{MAX_COOKING_TIME} минут.'
            )
        ]
    )
    image = models.ImageField(
        verbose_name='Изображение',
        upload_to='recipes/',
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        related_name='recipes',
        on_delete=models.CASCADE,
    )
    ingredients = models.ManyToManyField(
        'Ingredient',
        through='RecipeIngredient',
        verbose_name='Ингридиенты',
        related_name='recipes'
    )
    tags = models.ManyToManyField(
        'Tag',
        verbose_name='Теги',
        related_name='recipes'
    )
    short_link = models.CharField(
        max_length=MAX_LENGTH_SHORT_LINK,
        unique=True,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-created_at',)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Сохраняет рецепт, генерируя короткую ссылку при необходимости."""
        if not self.short_link:
            self.short_link = self.generate_unique_short_url()
        super().save(*args, **kwargs)

    def generate_unique_short_url(self, length=MAX_LENGTH_SHORT_LINK):
        """Генератор коротких ссылок."""
        while True:
            short_link = ''.join(
                random.choices(string.ascii_letters + string.digits, k=length)
            )
            if not Recipe.objects.filter(short_link=short_link).exists():
                return short_link


class Tag(models.Model):
    """Модель тега."""

    name = models.CharField(
        verbose_name='Название',
        max_length=MAX_LENGTH_TAG,
        unique=True,
    )
    slug = models.SlugField(
        verbose_name='Слаг',
        max_length=MAX_LENGTH_TAG,
        unique=True,
    )

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель ингридиента."""

    name = models.CharField(
        verbose_name='Название',
        max_length=MAX_LENGTH_INGREDIENT_NAME,
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=MAX_LENGTH_MEASUREMENT_UNIT,
    )

    class Meta():
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_name_measurement_unit',
            ),
        )

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    """Модель для хранения количества ингредиентов в рецепте."""

    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        related_name='recipeingredients',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        related_name='recipeingredients',
        on_delete=models.CASCADE
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[
            MinValueValidator(
                MIN_AMOUNT,
                message='Количество ингредиента должно быть больше '
                f'{MIN_AMOUNT}.'
            ),
            MaxValueValidator(
                MAX_AMOUNT,
                message='Количество ингредиента не должно превышать '
                f'{MAX_AMOUNT}.'
            )
        ]
    )

    class Meta:
        verbose_name = 'количество ингридиента'
        verbose_name_plural = 'Количество ингридиентов'
        constraints = [
            UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient'
            )
        ]


class Favorite(models.Model):
    """Модель избранных рецептов."""

    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='favorites',
    )

    class Meta:
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранные'
        constraints = [
            UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favorite_user_recipe'
            )
        ]


class ShoppingList(models.Model):
    """Модель списка покупок."""

    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='shopping_lists',
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='shopping_lists',
    )

    class Meta:
        verbose_name = 'список покупок'
        verbose_name_plural = 'Список покупок'
        constraints = [
            UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe',
            )
        ]
