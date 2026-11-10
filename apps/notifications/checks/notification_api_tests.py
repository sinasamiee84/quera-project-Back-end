from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.notifications.services import create_notification

User = get_user_model()


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class NotificationAPIChecks(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            mobile="09121111111",
            password="password123",
        )
        self.user2 = User.objects.create_user(
            mobile="09122222222",
            password="password123",
        )

    def test_create_notification_service_creates_notification(self):
        notif = create_notification(
            user=self.user1,
            title="خوش آمدید",
            body="متن اعلان تست",
        )
        self.assertEqual(notif.user, self.user1)
        self.assertEqual(notif.title, "خوش آمدید")
        self.assertEqual(notif.body, "متن اعلان تست")
        self.assertEqual(notif.event_type, "system")
        self.assertEqual(notif.meta, {})
        self.assertFalse(notif.is_read)

    def test_list_requires_authentication(self):
        url = reverse("notifications-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_current_user_notifications(self):
        create_notification(user=self.user1, title="اعلان کاربر اول")
        create_notification(user=self.user2, title="اعلان کاربر دوم")

        self.client.force_authenticate(user=self.user1)
        url = reverse("notifications-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # هندل کردن ساختار صفحه‌بندی یا لیست مستقیم
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "اعلان کاربر اول")

    def test_mark_read_marks_current_user_notification(self):
        notif = create_notification(user=self.user1, title="اعلان خوانده‌نشده")
        self.client.force_authenticate(user=self.user1)

        url = reverse("notifications-mark-read", kwargs={"pk": notif.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_unread_count_counts_current_user_only(self):
        create_notification(user=self.user1, title="اعلان ۱ کاربر ۱")
        create_notification(user=self.user1, title="اعلان ۲ کاربر ۱")
        create_notification(user=self.user2, title="اعلان ۱ کاربر ۲")

        self.client.force_authenticate(user=self.user1)
        url = reverse("notifications-unread-count")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("unread_count"), 2)
