from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from api.views import redirect_short_link

urlpatterns = [
    path(
        's/<str:short_url>/', redirect_short_link, name='redirect-short-link'
    ),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
