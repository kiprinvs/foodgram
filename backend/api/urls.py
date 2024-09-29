from django.urls import include, path
from rest_framework.routers import DefaultRouter

router_v1 = DefaultRouter()

router_v1_urls = [

]

urlpatterns = [
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router_v1.urls))
]
