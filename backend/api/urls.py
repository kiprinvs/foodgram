from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (IngredientViewSet, MeView, RecipeViewSet,
                       SubscriptionsView, TagViewSet, UserViewSet)

app_name = 'api'

router_v1 = DefaultRouter()

router_v1_urls = [
    router_v1.register('recipes', RecipeViewSet, basename='recipes'),
    router_v1.register('tags', TagViewSet, basename='tags'),
    router_v1.register(
        'ingredients', IngredientViewSet, basename='ingredients'
    ),
    router_v1.register('users', UserViewSet, basename='users'),
]

urlpatterns = [
    path('users/me/', MeView.as_view()),
    path('users/subscriptions/', SubscriptionsView.as_view()),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router_v1.urls)),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
