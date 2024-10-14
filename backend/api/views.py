import random
import string

from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect

from djoser.views import UserViewSet as DjUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.response import Response

from recipes.models import Ingredient, Recipe, Tag, Favorite, ShoppingList, RecipeIngredient, ShortLink
from users.models import Subscribe
from .serializers import (
    AvatarUserSerializer, IngredientSerializer, RecipeSerializer, RecipeSubscribeSerializer,
    SubscribeSerializer, TagSerializer, UserCreateSerializer, UserSerializer, UserSerializer, ShortLinkSerializer,
    CustomTokenCreateSerializer
)

User = get_user_model()


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('tags__slug',)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        author_id = self.request.GET.get('author', None)
        tags = self.request.GET.getlist('tags')
        is_favorited = self.request.GET.get('is_favorited', None)
        is_in_shopping_cart = self.request.GET.get('is_in_shopping_cart', None)

        if author_id is not None:
            queryset = queryset.filter(author__id=author_id)

        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()

        if is_favorited:
            user = self.request.user
            favorite_recipe_ids = Favorite.objects.filter(
                user=user
            ).values_list('recipe_id')
            queryset = queryset.filter(id__in=favorite_recipe_ids)

        if is_in_shopping_cart:
            user = self.request.user
            shopping_cart_recipe_ids = ShoppingList.objects.filter(
                user=user
            ).values_list('recipe_id')
            queryset = queryset.filter(id__in=shopping_cart_recipe_ids)

        return queryset

    def destroy(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)

        if recipe.author != request.user:
            return Response(
                {'detail': 'У вас нет прав для удаления этого рецепта.'},
                status=status.HTTP_403_FORBIDDEN
            )

        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':

            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Нельзя добавить в избранное дважды.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            favorite = Favorite.objects.create(user=user, recipe=recipe)
            serializer = RecipeSubscribeSerializer(
                recipe, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            favorite = Favorite.objects.filter(
                user=user, recipe=recipe
            ).first()

            if favorite:
                favorite.delete()
                return Response(
                    {'detail': 'Вы убрали рецепт из избранного.'},
                    status=status.HTTP_204_NO_CONTENT
                )

            return Response(
                {'detail': 'Этого рецепта нет в избранном.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=('post', 'delete'),
            permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':

            if ShoppingList.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Вы уже добавили этот рецепт в список покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            shopping_cart = ShoppingList.objects.create(
                user=user, recipe=recipe
            )
            serializer = RecipeSubscribeSerializer(
                recipe, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            shopping_cart = ShoppingList.objects.filter(
                user=user, recipe=recipe
            ).first()

            if shopping_cart:
                shopping_cart.delete()
                return Response(
                    {'detai': 'Вы удалили рецепт из списка покупок.'},
                    status=status.HTTP_204_NO_CONTENT
                )

            return Response(
                {'detail': 'Этого рецепта нет в списке покупок.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """Скачать список покупок текущего пользователя в текстовом формате."""
        user = request.user
        shopping_list = ShoppingList.objects.filter(user=user)
        ingredients = RecipeIngredient.objects.filter(
            recipe__in=shopping_list.values_list('recipe', flat=True)
        )
        ingredient_count = {}

        for recipe_ingredient in ingredients:
            ingredient_name = recipe_ingredient.ingredient.name
            measurement_unit = recipe_ingredient.ingredient.measurement_unit
            amount = recipe_ingredient.amount

            if ingredient_name in ingredient_count:
                ingredient_count[ingredient_name]['amount'] += amount
            else:
                ingredient_count[ingredient_name] = {
                    'measurement_unit': measurement_unit,
                    'amount': amount
                }

        shopping_list_text = ''

        for name, data in ingredient_count.items():
            shopping_list_text += (
                f'{name} ({data["measurement_unit"]}) - '
                f'{data["amount"]}\n'
            )

        response = HttpResponse(shopping_list_text, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.txt"'
        )
        return response

    @action(detail=True, url_path='get-link')
    def get_link(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        short_link = ShortLink.objects.filter(recipe=recipe).first()

        if not short_link:
            short_url = self.generate_unique_short_url()
            short_link = ShortLink.objects.create(
                recipe=recipe, short_url=short_url
            )

        serializer = ShortLinkSerializer(
            short_link, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def generate_unique_short_url(self):
        while True:
            length = 6
            short_url = ''.join(random.choices(
                string.ascii_letters + string.digits, k=length)
            )
            if not ShortLink.objects.filter(short_url=short_url).exists():
                return short_url


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    # permission_classes = (IsAdminUser,)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    # serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'token_create':  # Добавьте это условие
            return CustomTokenCreateSerializer
        return UserSerializer

    @action(detail=False, url_path='me', permission_classes=(IsAuthenticated,))
    def me(self, request):
        print("вызов me")
        serializer = UserSerializer(
            request.user,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=['put'], url_path='me/avatar',
            permission_classes=(IsAuthenticated,))
    def update_avatar(self, request):
        print("request update.data", request.data)
        user = request.user
        serializer = AvatarUserSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @update_avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user

        if user.avatar:
            user.avatar.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='subscribe',
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, pk=None):
        subscribed_user = get_object_or_404(User, id=pk)
        user = request.user

        if user == subscribed_user:
            return Response(
                {'detail': 'Нельзя подписаться на самого себя.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Subscribe.objects.filter(
            user=user, subscribed_user=subscribed_user
        ).exists():
            return Response(
                {'detail': 'Вы уже подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        Subscribe.objects.create(
            user=user, subscribed_user=subscribed_user
        )
        serializer = SubscribeSerializer(
            subscribed_user, context={'request': request}
        )
        return Response(
            serializer.data, status=status.HTTP_201_CREATED
        )

    @subscribe.mapping.delete
    def unsubscribe(self, request, pk=None):
        subscribed_user = get_object_or_404(User, id=pk)
        subscription = Subscribe.objects.filter(
            user=request.user, subscribed_user=subscribed_user
        ).first()

        if subscription:
            subscription.delete()
            return Response(
                {'detail': 'Вы отписались от пользователя.'},
                status=status.HTTP_204_NO_CONTENT
            )

        return Response(
            {'detail': 'Вы не подписаны на этого пользователя.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def subscriptions(self, request):
        subscriptions = Subscribe.objects.filter(user=request.user)
        following_users = [sub.subscribed_user for sub in subscriptions]
        page = self.paginate_queryset(following_users)
        serializer = SubscribeSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def redirect_short_link(request, short_url):
    short_link = get_object_or_404(ShortLink, short_url=short_url)
    host = get_current_site(request)
    recipe_id = short_link.recipe.pk
    redirect_url = f"http://{host.domain}/recipes/{recipe_id}"
    return redirect(redirect_url)
