from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("title", "user", "is_read", "created_at")
    search_fields = ("title", "body", "user__mobile")
    list_filter = ("is_read", "created_at")
