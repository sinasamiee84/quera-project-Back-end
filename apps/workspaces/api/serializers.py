from rest_framework import serializers

from apps.users.api.serializers import UserSerializer
from apps.users.models import User
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.workspaces.permissions import get_workspace_role


class AbsoluteImageField(serializers.ImageField):
    def to_representation(self, value):
        if not value:
            return None

        url = value.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class WorkspaceSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()
    thumbnail = AbsoluteImageField(required=False, allow_null=True)

    class Meta:
        model = Workspace
        fields = (
            "id",
            "name",
            "description",
            "thumbnail",
            "owner",
            "my_role",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "created_at",
            "updated_at",
        )
        validators = []

    def get_my_role(self, obj):
        request = self.context.get("request")
        if request is None:
            return None
        return get_workspace_role(request.user, obj)

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError(
                "Name cannot be blank."
            )

        request = self.context.get("request")
        owner = self.instance.owner if self.instance else (
            request.user if request else None
        )

        if owner is not None:
            duplicates = Workspace.objects.filter(
                owner=owner,
                name=name,
                is_deleted=False,
            )
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)

            if duplicates.exists():
                raise serializers.ValidationError(
                    "You already have a workspace with this name."
                )

        return name


class WorkspaceMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.all(),
        write_only=True,
    )

    class Meta:
        model = WorkspaceMembership
        fields = (
            "id",
            "workspace",
            "user",
            "user_id",
            "role",
            "is_active",
            "joined_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "joined_at",
            "created_at",
            "updated_at",
        )
        validators = []

    def to_internal_value(self, data):
        data = data.copy()

        if "user_id" not in data and "user" in data:
            data["user_id"] = data["user"]

        return super().to_internal_value(data)

    def validate(self, attrs):
        workspace = attrs.get("workspace")
        user = attrs.get("user")

        if self.instance is not None:
            workspace = workspace or self.instance.workspace
            user = user or self.instance.user

            if workspace.pk != self.instance.workspace_id:
                raise serializers.ValidationError({
                    "workspace": "Cannot change the workspace of an existing membership."
                })
            if user.pk != self.instance.user_id:
                raise serializers.ValidationError({
                    "user_id": "Cannot change the user of an existing membership."
                })

        if workspace is not None and user is not None:
            duplicates = WorkspaceMembership.objects.filter(
                workspace=workspace,
                user=user,
                is_deleted=False,
            )
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)

            if duplicates.exists():
                raise serializers.ValidationError({
                    "user_id": "This user is already a member of this workspace."
                })

        return attrs
