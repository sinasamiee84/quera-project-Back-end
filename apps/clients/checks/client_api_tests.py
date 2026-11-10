from django.test import override_settings
from rest_framework.test import APITestCase

from apps.clients.models import Client
from apps.notifications.models import Notification
from apps.users.models import User
from apps.workspaces.models import Workspace, WorkspaceMembership


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)
class ClientApiChecks(APITestCase):
    url = "/api/clients/"

    def setUp(self):
        self.owner = User.objects.create_user(
            mobile="09120000001",
            password="testpass123",
        )
        self.member = User.objects.create_user(
            mobile="09120000002",
            password="testpass123",
        )
        self.other_owner = User.objects.create_user(
            mobile="09120000003",
            password="testpass123",
        )

        self.workspace = Workspace.objects.create(
            name="Main Workspace",
            owner=self.owner,
        )
        self.hidden_workspace = Workspace.objects.create(
            name="Hidden Workspace",
            owner=self.other_owner,
        )

        WorkspaceMembership.objects.get_or_create(
            workspace=self.workspace,
            user=self.member,
            defaults={"role": "member", "is_active": True},
        )

        self.existing_client = Client.objects.create(
            workspace=self.workspace,
            name="Existing Client",
        )

    def test_owner_can_create_client(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {
                "workspace_id": self.workspace.pk,
                "name": "New Client",
                "email": "new@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            Client.objects.filter(
                workspace=self.workspace,
                name="New Client",
            ).exists()
        )

    def test_member_only_sees_visible_clients(self):
        hidden_client = Client.objects.create(
            workspace=self.hidden_workspace,
            name="Hidden Client",
        )
        self.client.force_authenticate(user=self.member)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.data)
        names = {item["name"] for item in response.data["results"]}
        self.assertIn(self.existing_client.name, names)
        self.assertNotIn(hidden_client.name, names)

    def test_duplicate_name_is_rejected_in_workspace(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {
                "workspace_id": self.workspace.pk,
                "name": self.existing_client.name,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("name", response.data)
        self.assertIn("already", str(response.data["name"]).lower())

    def test_member_cannot_create_client_in_hidden_workspace(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            self.url,
            {
                "workspace_id": self.hidden_workspace.pk,
                "name": "Unauthorized Client",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("workspace", response.data)
        self.assertFalse(
            Client.objects.filter(
                workspace=self.hidden_workspace,
                name="Unauthorized Client",
            ).exists()
        )

    def test_client_creation_creates_notification(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {
                "workspace_id": self.workspace.pk,
                "name": "Notified Client",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)

        notification = Notification.objects.filter(
            user=self.member,
            event_type="client_created",
        ).first()
        self.assertIsNotNone(notification)
        self.assertEqual(
            notification.meta["workspace_name"],
            self.workspace.name,
        )
