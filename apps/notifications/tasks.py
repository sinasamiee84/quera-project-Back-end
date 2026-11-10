from celery import shared_task

from apps.notifications.services import create_notification
from apps.users.models import User


@shared_task
def create_notification_task(user_id, title, body=""):
    user = User.objects.get(pk=user_id)
    notification = create_notification(user=user, title=title, body=body)
    return str(notification.pk)
