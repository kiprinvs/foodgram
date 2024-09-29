from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import UniqueConstraint

User = get_user_model()


class Recipe(models.Model):
    """Модель рецепта."""

    name = models.CharField(
        verbose_name='Название',
        max_length=256
    )
    description = models.TextField(
        verbose_name='Описание',
    )
    cooking_time = models.PositiveIntegerField(
        verbose_name='Время приготовления(в минутах)'
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
        through='IngredientRecipe',
        verbose_name='Ингридиенты',
        related_name='recipes'
    )
    tags = models.ManyToManyField(
        'Tag',
        verbose_name='Теги',
        related_name='recipes'
    )

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Модель тега."""

    name = models.CharField(
        verbose_name='Название',
        max_length=32,
        unique=True,
    )
    slug = models.SlugField(
        verbose_name='Слаг',
        max_length=32,
        unique=True,
    )

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель ингридиента."""

    name = models.CharField(
        verbose_name='Название',
        max_length=256,
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=50,
    )

    def __str__(self):
        return self.name


class IngredientRecipe(models.Model):
    """Модель для хранения количества ингредиентов в рецепте."""

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Количество ингридиента'
        constraints = [
            UniqueConstraint(
                fields=['recipe', 'ingredient'],
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
        verbose_name = 'Избранное'


class ShoppingList(models.Model):
    """Модель списка покупок."""

    user = user = models.ForeignKey(
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
        verbose_name = 'Список покупок'
        constraints = [
            UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe',
            )
        ]
