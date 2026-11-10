from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import secrets
from django.core.cache import cache
from apps.notifications.api.serializers import NotificationSerializer
from apps.notifications.models import Notification
import time
import json
from django.http import HttpResponse , StreamingHttpResponse


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"updated": updated})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread_count": count})


class NotificationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        total_count = qs.count()
        unread_count = qs.filter(is_read=False).count()
        serializer = NotificationSerializer(qs, many=True)
        return Response(
            {
                "count": total_count,
                "unread_count": unread_count,
                "notifications": serializer.data,
            }
        )


class NotificationSeenAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        notif_id = request.data.get("id")
        if not notif_id:
            return Response({"updated": 0})

        updated = Notification.objects.filter(id=notif_id, user=request.user, is_read=False).update(is_read=True)
        return Response({"updated": updated})


class NotificationSeenAllAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"updated": updated})


class NotificationStreamTokenAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = secrets.token_hex(16)
        # اصلاح: notifications جمع و sse (نه see)
        cache_key = f"notifications:sse:{token}"
        expires_in = 300
        cache.set(cache_key, str(request.user.id), timeout=expires_in)
        return Response({
            "token": token,
            "expires_in": expires_in,
        }, status=status.HTTP_200_OK)


def notification_stream(request):
    token = (request.GET.get("token") or "").strip()
    if not token:
        return HttpResponse("Missing token.", status=401)

    cached_user_id = cache.get(f"notifications:sse:{token}")
    if not cached_user_id:
        return HttpResponse("Invalid or expired token.", status=401)

    def events():
        last_id = None
        for _ in range(3):
            notification = Notification.objects.filter(user_id=cached_user_id).order_by("-created_at").first()
            if notification and notification.id != last_id:
                last_id = notification.id
                payload = NotificationSerializer(notification).data
                # اصلاح: ensure_ascii=False برای پشتیبانی از حروف فارسی
                payload_json = json.dumps(payload, default=str, ensure_ascii=False)
                yield f"event: notification\ndata: {payload_json}\n\n"
            else:
                yield "event: ping\ndata: {}\n\n"
            time.sleep(0.1)

    response = StreamingHttpResponse(events(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response












