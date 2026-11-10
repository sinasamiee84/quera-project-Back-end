from rest_framework.routers import DefaultRouter
from .views import WorkspaceMembershipViewSet
router = DefaultRouter()
router.register("", WorkspaceMembershipViewSet, basename="membership")
urlpatterns = router.urls
