import base64

from django.contrib.auth import get_user_model
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.sites.shortcuts import get_current_site
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer as DjUserCreateSerializer
from djoser.serializers import UserSerializer as DjUserSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, ShortLink, Tag)
from users.constants import MAX_LENGTH_EMAIL, MAX_LENGTH_NAME
from users.models import Subscribe

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):

        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


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
        user = self.context.get('request').user

        if not user.is_authenticated:
            return False

        return Subscribe.objects.filter(
            user=user, subscribed_user=subscribed_user
        ).exists()


class UserCreateSerializer(DjUserCreateSerializer):

    email = serializers.EmailField(max_length=MAX_LENGTH_EMAIL, required=True)
    username = serializers.CharField(
        max_length=MAX_LENGTH_NAME,
        required=True,
        validators=(UnicodeUsernameValidator(),),
    )

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'password'
        )

    def validate(self, data):
        user_by_email = User.objects.filter(email=data['email']).first()
        user_by_username = User.objects.filter(
            username=data['username']
        ).first()
        error_msg = {}

        if user_by_email is not None:
            error_msg['email'] = (
                'Пользователь с таким email уже существует.'
            )

        if user_by_username is not None:
            error_msg['username'] = (
                'Пользователь с таким username уже существует.'
            )

        if error_msg:
            raise serializers.ValidationError(error_msg)

        return data


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class CreateRecipeIngredientSerializer(serializers.ModelSerializer):
    amount = serializers.IntegerField()
    id = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')

    def validate_id(self, value):
        if not Ingredient.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                f"Ингредиент с id {value} не существует."
            )
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Количество ингредиента должно быть больше 0.'
            )
        return value


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug',)


class RecipeDetailSerializer(serializers.ModelSerializer):
    text = serializers.CharField(source='description')
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name',
            'image', 'text', 'cooking_time',
        )


class RecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=True, allow_null=True)
    text = serializers.CharField(source='description')
    author = UserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all()
    )
    ingredients = CreateRecipeIngredientSerializer(
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

    def validate(self, data):
        ingredients = data.get('recipeingredients')
        tags = data.get('tags')
        cooking_time = data.get('cooking_time')

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

        if cooking_time <= 0:
            raise serializers.ValidationError(
                'Время приготовления должно быть больше 0.'
            )

        return data

    def create(self, validated_data):
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('recipeingredients')
        recipe = Recipe.objects.create(**validated_data)

        for tag in tags_data:
            recipe.tags.add(tag)

        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data['id']
            amount = ingredient_data['amount']
            if ingredient_id and amount:
                ingredient = get_object_or_404(Ingredient, id=ingredient_id)
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    amount=amount
                )
        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.image = validated_data.get('image', instance.image)
        instance.description = validated_data.get(
            'description', instance.description
        )
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time
        )

        if 'tags' in validated_data:
            tags_data = validated_data.pop('tags')
            instance.tags.clear()
            for tag in tags_data:
                instance.tags.add(tag)

        if 'recipeingredients' in validated_data:
            ingredients_data = validated_data.pop('recipeingredients')
            instance.recipeingredients.all().delete()

            for ingredient_data in ingredients_data:
                ingredient_id = ingredient_data['id']
                amount = ingredient_data['amount']
                ingredient = get_object_or_404(Ingredient, id=ingredient_id)
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient,
                    amount=amount
                )

        instance.save()
        return instance

    def get_is_favorited(self, recipe):
        user = self.context.get('request').user
        if user.is_authenticated:
            return Favorite.objects.filter(user=user, recipe=recipe).exists()
        return False

    def get_is_in_shopping_cart(self, recipe):
        user = self.context.get('request').user
        if user.is_authenticated:
            return ShoppingList.objects.filter(
                user=user, recipe=recipe
            ).exists()
        return False

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        tags_info = TagSerializer(instance.tags, many=True).data
        ingredients_info = []

        for recipe_ingredient in instance.recipeingredients.all():
            ingredients_info.append(
                {
                    'id': recipe_ingredient.ingredient.id,
                    'name': recipe_ingredient.ingredient.name,
                    'measurement_unit': (
                        recipe_ingredient.ingredient.measurement_unit
                    ),
                    'amount': recipe_ingredient.amount
                }
            )

        representation['tags'] = tags_info
        representation['ingredients'] = ingredients_info
        return representation


class SubscribeSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar',
        )
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

    def get_recipes_count(self, subscribed_user):
        return Recipe.objects.filter(author=subscribed_user).count()

    def get_recipes(self, subscribed_user):
        request = self.context.get('request')
        recipes_limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=subscribed_user)
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        serializer = RecipeSubscribeSerializer(recipes, many=True)
        return serializer.data


class RecipeSubscribeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):
    recipe = RecipeSubscribeSerializer(read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Favorite
        fields = ('id', 'user', 'recipe')

    def create(self, validated_data):
        return super().create(validated_data)


class ShortLinkSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShortLink
        fields = ('short_url',)

    def to_representation(self, instance):
        """Преобразует ключи в формат с дефисом."""
        request = self.context.get('request')
        host = get_current_site(request)
        short_link = f"http://{host.domain}/s/{instance.short_url}"
        return {'short-link': short_link}
