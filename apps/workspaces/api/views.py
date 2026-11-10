from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.services import create_notification
from apps.workspaces.api.permissions import CanManageWorkspace
from apps.workspaces.api.serializers import (
    WorkspaceMembershipSerializer,
    WorkspaceSerializer,
)
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.workspaces.permissions import (
    get_workspace_role,
    has_workspace_role,
)


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = Workspace.objects.visible_to(self.request.user)

        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)

        ordering = self.request.query_params.get("ordering")
        allowed_orderings = {
            "name",
            "-name",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
        }
        if ordering in allowed_orderings:
            queryset = queryset.order_by(ordering)

        return queryset

    def get_object(self):
        workspace = super().get_object()

        if self.action in {"update", "partial_update", "destroy"}:
            if not CanManageWorkspace().has_object_permission(
                self.request, self, workspace
            ):
                raise PermissionDenied(
                    "شما دسترسی مدیریت این ورک‌اسپیس را ندارید."
                )

        return workspace

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["get"])
    def my_role(self, request, pk=None):
        workspace = self.get_object()
        return Response({
            "role": get_workspace_role(request.user, workspace)
        })


class WorkspaceMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceMembershipSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = WorkspaceMembership.objects.filter(
            workspace__in=Workspace.objects.visible_to(self.request.user),
            is_deleted=False,
        ).select_related("workspace", "user")

        workspace_id = self.request.query_params.get("workspace")
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        return queryset

    def _check_manage_permission(self, workspace):
        if not has_workspace_role(
            self.request.user,
            workspace,
            minimum_role="admin",
        ):
            raise PermissionDenied(
                "شما دسترسی مدیریت اعضای این ورک‌اسپیس را ندارید."
            )

    def get_object(self):
        membership = super().get_object()

        if self.action in {"update", "partial_update", "destroy"}:
            if not CanManageWorkspace().has_object_permission(
                self.request, self, membership
            ):
                raise PermissionDenied(
                    "شما دسترسی مدیریت اعضای این ورک‌اسپیس را ندارید."
                )

        return membership

    def perform_create(self, serializer):
        workspace = serializer.validated_data["workspace"]
        self._check_manage_permission(workspace)

        membership = serializer.save()

        create_notification(
            user=membership.user,
            title="افزودن به ورک‌اسپیس",
            body=f"شما به ورک‌اسپیس {workspace.name} افزوده شدید.",
            event_type="workspace_membership_added",
            meta={
                "workspace_id": str(workspace.pk),
                "workspace_name": workspace.name,
            },
        )

    def perform_update(self, serializer):
        membership = serializer.instance
        old_role = membership.role

        membership = serializer.save()

        if membership.role != old_role:
            create_notification(
                user=membership.user,
                title="تغییر نقش در ورک‌اسپیس",
                body=(
                    f"نقش شما در ورک‌اسپیس "
                    f"{membership.workspace.name} تغییر کرد."
                ),
                event_type="workspace_membership_role_changed",
                meta={
                    "workspace_id": str(membership.workspace_id),
                    "workspace_name": membership.workspace.name,
                    "new_role": membership.role,
                },
            )

    def perform_destroy(self, instance):
        user = instance.user
        workspace = instance.workspace

        instance.delete()

        create_notification(
            user=user,
            title="حذف از ورک‌اسپیس",
            body=f"عضویت شما در ورک‌اسپیس {workspace.name} لغو شد.",
            event_type="workspace_membership_removed",
            meta={
                "workspace_id": str(workspace.pk),
                "workspace_name": workspace.name,
            },
        )
