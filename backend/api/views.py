from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import CustomLimitPagination
from api.permissions import IsAuthorOrAuthenticatedOrReadOnly
from api.serializers import (AvatarUserSerializer, FavoriteSerializer,
                             IngredientSerializer, RecipeCreateSerializer,
                             RecipeSerializer, ShoppingCartSerializer,
                             SubscribeCreateSerializer, SubscribeSerializer,
                             TagSerializer, UserSerializer)
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Tag)
from users.models import Subscribe

User = get_user_model()


class RecipeViewSet(viewsets.ModelViewSet):
    """Администрирование рецептов."""
    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('tags__slug',)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeSerializer
        return RecipeCreateSerializer

    def get_permissions(self):
        if self.action == 'create':
            return (IsAuthenticated(),)
        elif self.action in ('destroy', 'partial_update'):
            return (IsAuthorOrAuthenticatedOrReadOnly(),)
        return super().get_permissions()

    @action(
        detail=True, methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk):
        """Добавление рецепта в избранное."""
        recipe = get_object_or_404(Recipe, pk=pk)
        favorite_data = {'user': request.user.id, 'recipe': recipe.id}
        serializer = FavoriteSerializer(data=favorite_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def remove_favorite(self, request, pk=None):
        """Удаление рецепта из избранного."""
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted_count, _ = Favorite.objects.filter(
            user=request.user, recipe=recipe
        ).delete()

        if not deleted_count:
            return Response(
                {'detail': 'Этого рецепта нет в избранном.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {'detail': 'Вы удалили рецепт из избранного.'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=('post',),
            permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk):
        """Добавление рецепта в список покупок."""
        recipe = get_object_or_404(Recipe, pk=pk)
        shopping_cart_data = {'user': request.user.id, 'recipe': recipe.id}
        serializer = ShoppingCartSerializer(data=shopping_cart_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def remove_shopping_cart(self, request, pk=None):
        """Удаление рецепта из списка покупок."""
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted_count, _ = ShoppingList.objects.filter(
            user=request.user, recipe=recipe
        ).delete()

        if not deleted_count:
            return Response(
                {'detail': 'Этого рецепта нет в списке покупок.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {'detail': 'Вы удалили рецепт из списка покупок.'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """Скачать список покупок текущего пользователя в текстовом формате."""
        user = request.user
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_lists__user=user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        )
        shopping_list_text = ''

        for ingredient in ingredients:
            shopping_list_text += (
                f'{ingredient["ingredient__name"]} '
                f'({ingredient["ingredient__measurement_unit"]}) - '
                f'{ingredient["total_amount"]}\n'
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
        short_link = f'http://{request.get_host()}/s/{recipe.short_link}/'
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)


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
    serializer_class = UserSerializer

    @action(
        detail=False,
        methods=['get'],
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        """Метод для получения информации о текущем пользователе."""
        return super().me(request)

    @action(
        detail=False,
        methods=('put',),
        url_path='me/avatar',
        permission_classes=(IsAuthenticated,)
    )
    def avatar(self, request):
        """Установка и удаление аватара."""
        user = request.user
        serializer = AvatarUserSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @avatar.mapping.delete
    def remove_avatar(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, **kwargs):
        """Подписка."""
        subscribed_user = get_object_or_404(User, id=self.kwargs.get('id'))
        subscribe_data = {
            'user': request.user.id, 'subscribed_user': subscribed_user.id
        }
        serializer = SubscribeCreateSerializer(
            data=subscribe_data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def remove_subscribe(self, request, **kwargs):
        subscribed_user = get_object_or_404(User, id=self.kwargs.get('id'))
        subscription = Subscribe.objects.filter(
            user=request.user.id, subscribed_user=subscribed_user.id
        ).first()

        if not subscription:
            return Response(
                {'detail': 'Вы не подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription.delete()
        return Response(
            {'detail': 'Вы отписались от пользователя.'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        """Метод для получения подписок текущего пользователя."""
        subscriptions = Subscribe.objects.filter(user=self.request.user)
        following_users = [sub.subscribed_user for sub in subscriptions]
        pages = self.paginate_queryset(following_users)
        serializer = SubscribeSerializer(
            pages, many=True, context={'request': request}
        )

        return self.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def redirect_short_link(request, short_url):
    """Метод для редиректа с короткой ссылки."""
    recipe = get_object_or_404(Recipe, short_link=short_url)
    host = get_current_site(request)
    redirect_url = f'http://{host.domain}/recipes/{recipe.id}/'
    return HttpResponseRedirect(redirect_url)
