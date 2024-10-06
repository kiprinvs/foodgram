from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.response import Response

from recipes.models import Ingredient, Recipe, Tag
from .serializers import AvatarUserSerializer, IngredientSerializer, RecipeSerializer, TagSerializer, UserCreateSerializer, UserSerializer, UserSerializer

User = get_user_model()


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


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

    #def get_serializer_class(self):
    #    print('!!!!!!!!!!!!!!!!!!!')
    #    if self.action in ('list', 'retrieve'):
    #        return UserSerializer
    #    return UserCreateSerializer

    @action(detail=False, permission_classes=(IsAuthenticated,))
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
