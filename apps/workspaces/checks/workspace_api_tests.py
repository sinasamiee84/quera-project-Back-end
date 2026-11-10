from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.users.models import User
from apps.workspaces.models import Workspace, WorkspaceMembership


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)
class WorkspaceApiChecks(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            mobile="09120000001",
            password="test-password",
        )
        self.member = User.objects.create_user(
            mobile="09120000002",
            password="test-password",
        )
        self.target = User.objects.create_user(
            mobile="09120000003",
            password="test-password",
        )
        self.other = User.objects.create_user(
            mobile="09120000004",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Team",
            owner=self.owner,
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.member,
            role=WorkspaceMembership.Role.MEMBER,
        )

    def test_owner_can_create_workspace(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/api/workspaces/",
            {"name": "New workspace"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Workspace.objects.filter(
                name="New workspace",
                owner=self.owner,
            ).exists()
        )

    def test_member_only_sees_joined_workspaces(self):
        other_workspace = Workspace.objects.create(
            name="Other workspace",
            owner=self.other,
        )
        self.client.force_authenticate(user=self.member)

        response = self.client.get("/api/workspaces/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = (
            response.data["results"]
            if isinstance(response.data, dict)
            else response.data
        )
        ids = {row["id"] for row in rows}

        self.assertIn(self.workspace.pk, ids)
        self.assertNotIn(other_workspace.pk, ids)

    def test_owner_can_add_member(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/api/workspace-memberships/",
            {
                "workspace": self.workspace.pk,
                "user_id": self.target.pk,
                "role": "member",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            WorkspaceMembership.objects.filter(
                workspace=self.workspace,
                user=self.target,
            ).exists()
        )

    def test_member_cannot_add_member(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            "/api/workspace-memberships/",
            {
                "workspace": self.workspace.pk,
                "user_id": self.target.pk,
                "role": "member",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_adding_member_creates_notification(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/api/workspace-memberships/",
            {
                "workspace": self.workspace.pk,
                "user_id": self.target.pk,
                "role": "member",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Notification.objects.filter(
                user=self.target,
                event_type="workspace_membership_added",
            ).exists()
        )

    def test_duplicate_workspace_name_for_same_owner_is_rejected(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/api/workspaces/",
            {"name": "  Team  "},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_duplicate_workspace_membership_is_rejected(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/api/workspace-memberships/",
            {
                "workspace": self.workspace.pk,
                "user": self.member.pk,
                "role": "member",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_member_creates_notification_for_target_user(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/api/memberships/",
            {
                "workspace": self.workspace.pk,
                "user": self.target.pk,
                "role": "member",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Notification.objects.filter(
                user=self.target,
                event_type="workspace_membership_added",
            ).exists()
        )
        self.assertFalse(
            Notification.objects.filter(
                user=self.owner,
                event_type="workspace_membership_added",
            ).exists()
        )

    def test_role_change_creates_notification_for_target_user(self):
        membership = WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.target,
            role=WorkspaceMembership.Role.MEMBER,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            f"/api/workspace-memberships/{membership.pk}/",
            {"role": "admin"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership.refresh_from_db()
        self.assertEqual(membership.role, "admin")
        self.assertTrue(
            Notification.objects.filter(
                user=self.target,
                event_type="workspace_membership_role_changed",
            ).exists()
        )
        self.assertFalse(
            Notification.objects.filter(
                user=self.owner,
                event_type="workspace_membership_role_changed",
            ).exists()
        )
