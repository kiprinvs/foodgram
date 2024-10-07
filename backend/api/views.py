from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.response import Response

from recipes.models import Ingredient, Recipe, Tag
from .serializers import AvatarUserSerializer, IngredientSerializer, RecipeSerializer, TagSerializer, UserCreateSerializer, UserSerializer, UserSerializer

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
        author_id = self.request.query_params.get('author', None)
        tags = self.request.query_params.getlist('tags')

        if author_id is not None:
            queryset = queryset.filter(author__id=author_id)

        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()

        return queryset

    def destroy(self, request, pk=None):
        recipe = self.get_object()
        if recipe.author != request.user:
            return Response({'detail': 'У вас нет прав для удаления этого рецепта.'}, status=status.HTTP_403_FORBIDDEN)

        recipe.delete()  # Удаляем рецепт
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, pk=None):
        print(f"Retrieve method called for user ID: {pk}")  # Отладка
        user = get_object_or_404(User, id=pk)
        serializer = UserSerializer(user)
        return Response(serializer.data)