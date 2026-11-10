from rest_framework.permissions import BasePermission

from apps.workspaces.models import WorkspaceMembership
from apps.workspaces.permissions import has_workspace_role


class CanManageWorkspace(BasePermission):
    message = "شما دسترسی مدیریت این ورک‌اسپیس را ندارید."

    def has_object_permission(self, request, view, obj):
        workspace = (
            obj.workspace
            if isinstance(obj, WorkspaceMembership)
            else obj
        )
        return has_workspace_role(
            request.user,
            workspace,
            minimum_role="admin",
        )
