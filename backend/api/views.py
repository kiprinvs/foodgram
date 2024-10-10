from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.response import Response

from recipes.models import Ingredient, Recipe, Tag, Favorite
from users.models import Subscribe
from .serializers import (
    AvatarUserSerializer, IngredientSerializer, RecipeSerializer, RecipeSubscribeSerializer,
    SubscribeSerializer, TagSerializer, UserCreateSerializer, UserSerializer, UserSerializer,
    FavoriteSerializer,
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
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

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
