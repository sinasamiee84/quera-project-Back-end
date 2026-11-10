from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.notifications.api.views import (
    NotificationListAPIView,
    NotificationSeenAPIView,
    NotificationSeenAllAPIView,
    NotificationViewSet,
    NotificationStreamTokenAPIView,
    notification_stream
)

router = DefaultRouter()
router.register("", NotificationViewSet, basename="notifications")

urlpatterns = [
    path("stream-token/", NotificationStreamTokenAPIView.as_view(), name="stream-token"),
    path("stream/", notification_stream, name="stream"),
    path("list/", NotificationListAPIView.as_view(), name="notification-list-legacy"),
    path("seen/", NotificationSeenAPIView.as_view(), name="notification-seen"),
    path("seen/all/", NotificationSeenAllAPIView.as_view(), name="notification-seen-all"),
    path("", include(router.urls)),
]