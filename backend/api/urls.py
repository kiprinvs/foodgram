from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import IngredientViewSet, RecipeViewSet

router_v1 = DefaultRouter()

router_v1_urls = [
    router_v1.register('recipes', RecipeViewSet),
    router_v1.register('ingredients', IngredientViewSet)
]

urlpatterns = [
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router_v1.urls))
]
