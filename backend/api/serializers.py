import base64

from django.contrib.auth import get_user_model
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
#from djoser.serializers import UserCreateSerializer, UserSerializer
from djoser.serializers import UserSerializer as DjoserUserSerializer
from djoser.serializers import UserCreateSerializer as DjoserUserCreateSerializer
from rest_framework import serializers

from recipes.models import (
    Favorite, Ingredient, RecipeIngredient, Recipe, RecipeTag, ShoppingList, Tag
)
from users.constants import MAX_LENGTH_EMAIL, MAX_LENGTH_NAME

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


class UserSerializer(DjoserUserSerializer):
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'avatar')

    def validate(self, data):
        print(data)
        user_by_email = User.objects.filter(
            email=data['email']
        ).first()
        print(user_by_email)
        user_by_username = User.objects.filter(
            username=data['username']
        ).first()
        print(user_by_username)
        if user_by_email != user_by_username:
            error_msg = {}
            if user_by_email is not None:
                error_msg['email'] = (
                    'Пользователь с таким email уже существует.'
                )
                print("Email error:", error_msg['email'])
            if user_by_username is not None:
                error_msg['username'] = (
                    'Пользователь с таким username уже существует.'
                )
            raise serializers.ValidationError(error_msg)
        return data


class UserCreateSerializer(DjoserUserCreateSerializer):

    email = serializers.EmailField(max_length=MAX_LENGTH_EMAIL, required=True)
    username = serializers.CharField(
        max_length=MAX_LENGTH_NAME,
        required=True,
        # validators=(UnicodeUsernameValidator(),),
    )

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'password'
        )

    def validate(self, data):
        print(data)
        user_by_email = User.objects.filter(
            email=data['email']
        ).first()
        print(user_by_email)
        user_by_username = User.objects.filter(
            username=data['username']
        ).first()
        print(user_by_username)
        if user_by_email != user_by_username:
            error_msg = {}
            if user_by_email is not None:
                error_msg['email'] = (
                    'Пользователь с таким email уже существует.'
                )
                print("Email error:", error_msg['email'])
            if user_by_username is not None:
                error_msg['username'] = (
                    'Пользователь с таким username уже существует.'
                )
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
            raise serializers.ValidationError(f"Ингредиент с id {value} не существует.")
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
    image = Base64ImageField(required=False, allow_null=True)
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
            'id', 'tags', 'author', 'ingredients', 'name',
            'image', 'text', 'cooking_time'
        )
        read_only_fields = ('author',)

    def create(self, validated_data):
        print("validated_data", validated_data)
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('recipeingredients')
        recipe = Recipe.objects.create(**validated_data)
        print('tags', tags_data, 'ingredients', ingredients_data)

        for tag in tags_data:
            recipe.tags.add(tag)

        for ingredient_data in ingredients_data:
            print(ingredient_data)
            ingredient_id = ingredient_data['id']
            amount = ingredient_data['amount']
            print(amount)
            if ingredient_id and amount:
                ingredient = get_object_or_404(Ingredient, id=ingredient_id)
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    amount=amount
                )
        return recipe

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
