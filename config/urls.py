from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.workspaces.urls',namespace='workspaces')),
    path('auth/', include('apps.users.urls',namespace='users')),
    path('api/users/', include('apps.users.api.urls',namespace='api-users')),
    path("api/notifications/", include("apps.notifications.api.urls")),

]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
