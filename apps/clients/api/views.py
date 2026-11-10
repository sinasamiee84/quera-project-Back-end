from rest_framework import viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from apps.clients.api.serializers import ClientSerializer
from apps.clients.models import Client
from apps.notifications.services import create_notification
from apps.workspaces.models import WorkspaceMembership


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = Client.objects.visible_to(self.request.user)

        workspace_id = self.request.query_params.get("workspace", "").strip()
        if workspace_id:
            # شناسهٔ نامعتبر نتیجهٔ خالی می‌دهد، نه خطای سرور.
            if not workspace_id.isdigit():
                return queryset.none()
            queryset = queryset.filter(workspace_id=int(workspace_id))

        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)

        ordering = self.request.query_params.get("ordering")
        if ordering in {"name", "-name", "created_at", "-created_at"}:
            queryset = queryset.order_by(ordering, "pk")

        return queryset

    def _notify_workspace_members(self, workspace, title, body, event_type):
        memberships = WorkspaceMembership.objects.filter(
            workspace=workspace,
            is_active=True,
            is_deleted=False,
        ).select_related("user")

        for membership in memberships:
            create_notification(
                user=membership.user,
                title=title,
                body=body,
                event_type=event_type,
                meta={
                    "workspace_id": str(workspace.pk),
                    "workspace_name": workspace.name,
                },
            )

    def perform_create(self, serializer):
        # دسترسیِ workspace پیش از save در serializer.validate بررسی می‌شود.
        client = serializer.save()

        self._notify_workspace_members(
            workspace=client.workspace,
            title="New client added",
            body=f"{client.name} was added to {client.workspace.name}.",
            event_type="client_created",
        )

    def perform_destroy(self, instance):
        workspace = instance.workspace
        client_name = instance.name

        instance.delete()

        self._notify_workspace_members(
            workspace=workspace,
            title="Client deleted",
            body=f"{client_name} was deleted from {workspace.name}.",
            event_type="client_deleted",
        )
