from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import IngredientViewSet, RecipeViewSet, TagViewSet, UserViewSet, SubscriptionsView

app_name = 'api'

router_v1 = DefaultRouter()

router_v1_urls = [
    router_v1.register('recipes', RecipeViewSet),
    router_v1.register('tags', TagViewSet),
    router_v1.register('ingredients', IngredientViewSet, basename='ingredients'),
    router_v1.register('users', UserViewSet, basename='users'),
]

urlpatterns = [
    path('users/subscriptions/', SubscriptionsView.as_view()),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router_v1.urls)),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
