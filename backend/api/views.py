import random
import string

from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjUserViewSet
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import CustomLimitPagination
from api.permissions import IsAuthor
from api.serializers import (AvatarUserSerializer, IngredientSerializer,
                             RecipeSerializer, RecipeSubscribeSerializer,
                             ShortLinkSerializer, SubscribeSerializer,
                             TagSerializer, UserCreateSerializer,
                             UserSerializer)
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, ShortLink, Tag)
from users.models import Subscribe

User = get_user_model()


class RecipeViewSet(viewsets.ModelViewSet):
    """Администрирование рецептов."""
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('tags__slug',)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_permissions(self):
        if self.action == 'create':
            return (IsAuthenticated(),)
        elif self.action in ('destroy', 'partial_update'):
            return (IsAuthor(),)
        return super().get_permissions()

    def destroy(self, request, pk=None):
        """Удаление рецепта."""
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
        """Избранное."""
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
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=('post', 'delete'),
            permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk):
        """Список покупок."""
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
                status=status.HTTP_400_BAD_REQUEST
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
        """Получение короткой ссылки."""
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
        """Генератор коротких ссылок."""
        while True:
            length = 6
            short_url = ''.join(random.choices(
                string.ascii_letters + string.digits, k=length)
            )
            if not ShortLink.objects.filter(short_url=short_url).exists():
                return short_url


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Теги."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (AllowAny,)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Получение ингредиентов."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class UserViewSet(DjUserViewSet):
    """Администрирование пользователей."""
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    pagination_class = CustomLimitPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    @action(
        detail=False,
        methods=['put', 'delete'],
        url_path='me/avatar',
        permission_classes=(IsAuthenticated,)
    )
    def avatar(self, request):
        """Установка и удаление аватара."""
        user = request.user

        if request.method == 'PUT':
            serializer = AvatarUserSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, **kwargs):
        """Подписка."""
        subscribed_user_id = self.kwargs.get('id')
        subscribed_user = get_object_or_404(User, id=subscribed_user_id)
        user = request.user

        if request.method == 'POST':
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
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            subscription = Subscribe.objects.filter(
                user=user, subscribed_user=subscribed_user
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


@api_view(['GET'])
@permission_classes([AllowAny])
def redirect_short_link(request, short_url):
    """Метод для редиректа с короткой ссылки."""
    short_link = get_object_or_404(ShortLink, short_url=short_url)
    host = get_current_site(request)
    recipe_id = short_link.recipe.pk
    redirect_url = f"http://{host.domain}/recipes/{recipe_id}"
    return redirect(redirect_url)


class SubscriptionsView(generics.ListAPIView):
    """Список подписок"""
    permission_classes = [IsAuthenticated]
    serializer_class = SubscribeSerializer

    def get_queryset(self):
        """Метод для получения подписок текущего пользователя."""
        user = self.request.user
        subscriptions = Subscribe.objects.filter(user=user)
        following_users = [sub.subscribed_user for sub in subscriptions]
        return following_users


class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """Метод для получения информации о текущем пользователе."""
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Необходима аутентификация.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
