from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.users.models import User


@shared_task
def create_notification_task(user_id, title, body=""):
    user = User.objects.get(pk=user_id)

    notification = create_notification(
        user=user,
        title=title,
        body=body,
    )

    return str(notification.pk)


@shared_task
def cleanup_read_notifications(days=30):
    cutoff_time = timezone.now() - timedelta(days=days)

    notifications = Notification.objects.filter(
        is_read=True,
        updated_at__lt=cutoff_time,
    )

    deleted_count = 0

    for notification in notifications:
        notification.delete()
        deleted_count += 1

    return deleted_count
