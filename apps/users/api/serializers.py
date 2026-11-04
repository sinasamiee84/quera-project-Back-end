from django.contrib.auth import authenticate
from rest_framework import serializers

from apps.users.models import User


def absolute_media_url(request, field):
    if not field:
        return None
    url = field.url
    return request.build_absolute_uri(url) if request else url


class UserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "mobile",
            "email",
            "first_name",
            "last_name",
            "birth_date",
            "description",
            "profile_picture",
            "date_joined",
        )
        read_only_fields = ("id", "date_joined")

    def get_profile_picture(self, obj):
        request = self.context.get("request")
        return absolute_media_url(request, obj.profile_picture)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("mobile", "password", "email", "first_name", "last_name")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def validate_mobile(self, value):
        if User.objects.filter(mobile=value).exists():
            raise serializers.ValidationError(
                "An account with this mobile number already exists."
            )
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value


class LoginSerializer(serializers.Serializer):
    mobile = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        mobile = attrs.get("mobile")
        password = attrs.get("password")
        request = self.context.get("request")

        user = authenticate(request=request, username=mobile, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials.")

        attrs["user"] = user
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value














