from rest_framework import serializers
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    # فیلدهایی که از دیتابیس مستقیم خوانده می‌شوند اما نامشان تغییر کرده
    message = serializers.ReadOnlyField(source='body')
    type = serializers.ReadOnlyField(source='event_type')
    is_seen = serializers.ReadOnlyField(source='is_read')

    # فیلدهای ثابت یا محاسباتی
    level = serializers.SerializerMethodField()
    delete_on_seen = serializers.SerializerMethodField()
    action_url = serializers.SerializerMethodField()
    entity_type = serializers.SerializerMethodField()
    entity_id = serializers.SerializerMethodField()
    meta = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'title', 'message', 'body', 'level',
            'created_at', 'is_read', 'is_seen', 'delete_on_seen',
            'action_url', 'entity_type', 'entity_id', 'meta'
        ]
        read_only_fields = fields

    # متدهای برای فیلدهای ثابت
    def get_level(self, obj):
        return 'info'

    def get_delete_on_seen(self, obj):
        return False

    def get_action_url(self, obj):
        return None

    def get_entity_type(self, obj):
        return None

    def get_entity_id(self, obj):
        return None

    # متد برای مدیریت دیکشنری خالی در meta
    def get_meta(self, obj):
        return obj.meta if obj.meta else {}
