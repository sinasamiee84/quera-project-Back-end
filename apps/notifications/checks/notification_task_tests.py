from django.test import override_settings
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.notifications.tasks import create_notification_task
from apps.users.models import User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class NotificationTaskChecks(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(mobile="09123456789")

    def test_task_creates_notification(self):
        create_notification_task(self.user.pk, "عنوان تست", "متن تست")
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, title="عنوان تست", body="متن تست"
            ).exists()
        )

    def test_task_returns_notification_id(self):
        result = create_notification_task(self.user.pk, "عنوان تست")
        notification = Notification.objects.get(user=self.user, title="عنوان تست")
        self.assertEqual(result, str(notification.pk))

    def test_task_stores_body(self):
        notification_id = create_notification_task(
            self.user.pk, "عنوان تست", "متن مشخص اعلان"
        )
        notification = Notification.objects.get(pk=notification_id)
        self.assertEqual(notification.body, "متن مشخص اعلان")

    def test_task_delay_runs_in_development_eager_mode(self):
        result = create_notification_task.delay(
            self.user.pk, "عنوان با تأخیر", "متن اعلان"
        )
        self.assertTrue(Notification.objects.filter(pk=result.get(timeout=5)).exists())

    def test_task_rejects_unknown_user(self):
        count_before = Notification.objects.count()
        with self.assertRaises(User.DoesNotExist):
            create_notification_task(self.user.pk + 1, "عنوان تست")
        self.assertEqual(Notification.objects.count(), count_before)
