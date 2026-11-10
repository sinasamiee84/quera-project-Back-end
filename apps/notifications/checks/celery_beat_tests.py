from datetime import timedelta

from django.conf import settings
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.notifications.tasks import cleanup_read_notifications
from apps.users.models import User


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)
class CeleryBeatChecks(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            mobile="09123456789"
        )

    def create_old_notification(self, *, is_read):
        notification = Notification.objects.create(
            user=self.user,
            title="اعلان قدیمی",
            body="متن اعلان",
            is_read=is_read,
        )

        old_time = timezone.now() - timedelta(days=31)

        Notification.objects.filter(
            pk=notification.pk
        ).update(updated_at=old_time)

        return notification

    def test_cleanup_task_soft_deletes_old_read_notifications(self):
        notification = self.create_old_notification(is_read=True)

        cleanup_read_notifications()

        self.assertFalse(
            Notification.objects.filter(
                pk=notification.pk
            ).exists()
        )

    def test_cleanup_task_keeps_unread_notifications(self):
        notification = self.create_old_notification(is_read=False)

        cleanup_read_notifications()

        self.assertTrue(
            Notification.objects.filter(
                pk=notification.pk
            ).exists()
        )

    def test_cleanup_task_returns_deleted_count(self):
        self.create_old_notification(is_read=True)
        self.create_old_notification(is_read=True)

        deleted_count = cleanup_read_notifications()

        self.assertEqual(deleted_count, 2)

    def test_beat_schedule_is_registered(self):
        self.assertIn(
            "cleanup-read-notifications",
            settings.CELERY_BEAT_SCHEDULE,
        )

    def test_beat_schedule_points_to_cleanup_task(self):
        schedule = settings.CELERY_BEAT_SCHEDULE[
            "cleanup-read-notifications"
        ]

        self.assertEqual(
            schedule["task"],
            "apps.notifications.tasks.cleanup_read_notifications",
        )

        self.assertEqual(schedule["schedule"], 3600.0)
