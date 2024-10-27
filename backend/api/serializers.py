from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer as DjUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Tag)
from users.models import Subscribe

User = get_user_model()


class AvatarUserSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class UserSerializer(DjUserSerializer):
    avatar = Base64ImageField(required=False)
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, subscribed_user):
        return bool(
            self.context.get('request')
            and self.context.get('request').user.is_authenticated
            and Subscribe.objects.filter(
                user=self.context.get('request').user,
                subscribed_user=subscribed_user
            ).exists()
        )


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(
        source='ingredient.name', read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class CreateRecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug',)


class RecipeCreateSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=True, allow_null=True)
    text = serializers.CharField(source='description')
    author = UserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all()
    )
    ingredients = CreateRecipeIngredientSerializer(
        many=True, source='recipeingredients'
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'name', 'image', 'text', 'cooking_time'
        )

    def validate_image(self, value):
        """Проверка на наличие изображения."""
        if not value:
            raise serializers.ValidationError(
                'Добавьте изображение рецепта.'
            )
        return value

    def validate(self, data):
        ingredients = data.get('recipeingredients')
        tags = data.get('tags')

        if not ingredients:
            raise serializers.ValidationError('Поле ingredients обязательное.')

        ingredient_ids = [ingredient['id'] for ingredient in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.'
            )

        if not tags:
            raise serializers.ValidationError(
                'Должен быть указан хотя бы один тег.'
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                'Теги не должны повторяться.'
            )

        return data

    def create(self, validated_data):
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('recipeingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('recipeingredients')
        instance = super().update(instance, validated_data)

        instance.tags.clear()
        instance.tags.set(tags_data)

        instance.ingredients.clear()
        self.create_ingredients(instance, ingredients_data)

        return instance

    @staticmethod
    def create_ingredients(recipe, ingredients_data):
        recipe_ingredients = []

        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data['id'].id
            amount = ingredient_data['amount']

            recipe_ingredients.append(
                RecipeIngredient(
                    recipe=recipe,
                    ingredient_id=ingredient_id,
                    amount=amount
                )
            )

        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data


class RecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=True, allow_null=True)
    text = serializers.CharField(source='description')
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source='recipeingredients'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('author',)

    def get_is_favorited(self, recipe):
        return bool(
            self.context.get('request')
            and self.context.get('request').user.is_authenticated
            and Favorite.objects.filter(
                user=self.context.get('request').user,
                recipe=recipe
            ).exists()
        )

    def get_is_in_shopping_cart(self, recipe):
        return bool(
            self.context.get('request')
            and self.context.get('request').user.is_authenticated
            and ShoppingList.objects.filter(
                user=self.context.get('request').user,
                recipe=recipe
            ).exists()
        )


class SubscribeCreateSerializer(UserSerializer):

    class Meta:
        model = Subscribe
        fields = ('user', 'subscribed_user')
        validators = [
            UniqueTogetherValidator(
                queryset=Subscribe.objects.all(),
                fields=('user', 'subscribed_user'),
                message='Нельзя подписаться дважды.'
            )
        ]

    def validate_subscribed_user(self, subscribed_user):

        if self.context.get('request').user == subscribed_user:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.'
            )

        return subscribed_user

    def to_representation(self, instance):
        return SubscribeSerializer(
            instance.subscribed_user, context=self.context
        ).data


class SubscribeSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar',
        )

    def get_recipes_count(self, subscribed_user):
        return Recipe.objects.filter(author=subscribed_user).count()

    def get_recipes(self, subscribed_user):
        request = self.context.get('request')
        recipes_limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=subscribed_user)
        if recipes_limit:
            try:
                recipes = recipes[:int(recipes_limit)]
            except ValueError:
                pass
        serializer = RecipeSubscribeSerializer(recipes, many=True)
        return serializer.data


class RecipeSubscribeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, data):
        if Favorite.objects.filter(
            user=data['user'], recipe=data['recipe']
        ).exists():
            raise serializers.ValidationError('Этот рецепт уже в избранном.')
        return data

    def to_representation(self, instance):
        return RecipeSubscribeSerializer(
            instance.recipe, context=self.context
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShoppingList
        fields = ('user', 'recipe')

    def validate(self, data):
        if ShoppingList.objects.filter(
            user=data['user'], recipe=data['recipe']
        ).exists():
            raise serializers.ValidationError(
                {'detail': 'Вы уже добавили этот рецепт в список покупок'},
            )
        return data

    def to_representation(self, instance):
        return RecipeSubscribeSerializer(
            instance.recipe, context=self.context
        ).data
