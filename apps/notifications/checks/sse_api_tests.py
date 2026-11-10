from django.core.cache import cache
from django.http import StreamingHttpResponse
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.users.models import User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SSEAPIChecks(APITestCase):
    def setUp(self):
        # ساخت کاربر با توجه به فیلد mobile پروژه شما
        self.user = User.objects.create_user(
            mobile="09120000000",
            password="testpassword123"
        )
        self.token_url = "/api/notifications/stream-token/"
        self.stream_url = "/api/notifications/stream/"

    def test_stream_token_requires_authentication(self):
        # بررسی اینکه بدون لاگین، گرفتن توکن خطای 401 می‌دهد
        response = self.client.post(self.token_url)
        self.assertEqual(response.status_code, 401)

    def test_stream_token_is_created_for_current_user(self):
        # احراز هویت کاربر و تست ساخت توکن و ذخیره در کش
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.token_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["expires_in"], 300)

        token = response.data["token"]
        cached_user_id = cache.get(f"notifications:sse:{token}")
        self.assertEqual(cached_user_id, str(self.user.id))

    def test_stream_rejects_invalid_token(self):
        # بررسی رد شدن توکن نامعتبر با خطای 401
        response = self.client.get(self.stream_url, {"token": "invalid-token-string"})
        self.assertEqual(response.status_code, 401)

    def test_stream_returns_streaming_response_for_valid_token(self):
        # بررسی بازگشت StreamingHttpResponse با توکن معتبر
        token = "valid-test-token-123"
        cache.set(f"notifications:sse:{token}", str(self.user.id), timeout=300)

        response = self.client.get(self.stream_url, {"token": token})
        self.assertIsInstance(response, StreamingHttpResponse)
        self.assertTrue(response["Content-Type"].startswith("text/event-stream"))
        response.close()

    def test_stream_sends_notification_event(self):
        # ایجاد اعلان و بررسی دریافت رویداد notification در خروجی استریم
        Notification.objects.create(
            user=self.user,
            title="اعلان تست",
            body="متن تست اعلان"
        )

        token = "valid-test-token-456"
        cache.set(f"notifications:sse:{token}", str(self.user.id), timeout=300)

        response = self.client.get(self.stream_url, {"token": token})
        try:
            first_chunk = next(iter(response.streaming_content))
            if isinstance(first_chunk, bytes):
                first_chunk = first_chunk.decode("utf-8")

            self.assertIn("event: notification", first_chunk)
            self.assertIn("اعلان تست", first_chunk)
            self.assertIn("متن تست اعلان", first_chunk)
        finally:
            response.close()
