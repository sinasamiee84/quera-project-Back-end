from django.conf import settings
from django.db import models
from core.models.base import TimestampedModel


class Notification(TimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        # مطمئن شو unique=True اینجا نیست!
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    event_type = models.CharField(max_length=100, default="system")
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.title
