from rest_framework.routers import DefaultRouter

from apps.clients.api.views import ClientViewSet


router = DefaultRouter()
router.register("", ClientViewSet, basename="clients")

urlpatterns = router.urls
