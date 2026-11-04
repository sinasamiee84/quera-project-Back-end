import base64
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.api.views import (
    LoginAPIView,
    LogoutAPIView,
    MeAPIView,
    PasswordChangeAPIView,
    ProfilePictureAPIView,
    RefreshAPIView,
    RegisterAPIView,
    UserSearchAPIView,
)


class AuthAPITests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.password = "ExamplePass_123"
        self.user = get_user_model().objects.create_user(
            mobile="09120000001",
            password=self.password,
        )

        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

    def call(self, view, method, path, data=None, authenticated=False):
        request = getattr(self.factory, method)(
            path, data=data or {}, format="json"
        )
        if authenticated:
            force_authenticate(request, user=self.user)
        return view.as_view()(request)

    def test_register_success(self):
        response = self.call(
            RegisterAPIView,
            "post",
            "/register/",
            {"mobile": "09120000002", "password": self.password},
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_register_duplicate_mobile(self):
        response = self.call(
            RegisterAPIView,
            "post",
            "/register/",
            {"mobile": self.user.mobile, "password": self.password},
        )
        self.assertEqual(response.status_code, 400)

    def test_login_success(self):
        response = self.call(
            LoginAPIView,
            "post",
            "/login/",
            {"mobile": self.user.mobile, "password": self.password},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_invalid_password(self):
        response = self.call(
            LoginAPIView,
            "post",
            "/login/",
            {"mobile": self.user.mobile, "password": "WrongPass_123"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access", response.data)

    def test_refresh_is_available_to_guest(self):
        refresh = RefreshToken.for_user(self.user)
        response = self.call(
            RefreshAPIView,
            "post",
            "/refresh/",
            {"refresh": str(refresh)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_me_requires_authentication(self):
        response = self.call(MeAPIView, "get", "/me/")
        self.assertIn(response.status_code, (401, 403))

    def test_me_returns_current_user(self):
        response = self.call(
            MeAPIView, "get", "/me/", authenticated=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["mobile"], self.user.mobile)

    def test_me_updates_profile(self):
        response = self.call(
            MeAPIView,
            "patch",
            "/me/",
            {"first_name": "Sara"},
            authenticated=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Sara")

    def test_logout_without_refresh_returns_204(self):
        response = self.call(
            LogoutAPIView,
            "post",
            "/logout/",
            authenticated=True,
        )
        self.assertEqual(response.status_code, 204)

    def test_logout_blacklists_submitted_refresh(self):
        refresh = RefreshToken.for_user(self.user)
        response = self.call(
            LogoutAPIView,
            "post",
            "/logout/",
            {"refresh_token": str(refresh)},
            authenticated=True,
        )
        self.assertEqual(response.status_code, 204)
        with self.assertRaises(TokenError):
            RefreshToken(str(refresh))

    def test_profile_picture_requires_file(self):
        response = self.call(
            ProfilePictureAPIView,
            "post",
            "/profile-picture/",
            authenticated=True,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {"profile_picture": "This file is required."},
        )

    def test_profile_picture_upload_and_delete(self):
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0"
            "lEQVR42mP8/x8AAwMCAO+/lZkAAAAASUVORK5CYII="
        )
        picture = SimpleUploadedFile(
            "avatar.png", png, content_type="image/png"
        )
        request = self.factory.post(
            "/profile-picture/",
            {"profile_picture": picture},
            format="multipart",
        )
        force_authenticate(request, user=self.user)

        upload = ProfilePictureAPIView.as_view()(request)
        self.assertEqual(upload.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_picture)

        delete = self.call(
            ProfilePictureAPIView,
            "delete",
            "/profile-picture/",
            authenticated=True,
        )
        self.assertEqual(delete.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_picture)

    def test_change_password(self):
        response = self.call(
            PasswordChangeAPIView,
            "patch",
            "/change-password/",
            {
                "old_password": self.password,
                "new_password": "AnotherPass_456",
            },
            authenticated=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {"detail": "Password changed."}
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("AnotherPass_456"))


    def test_search_requires_mobile_parameter(self):
        response = self.call(
            UserSearchAPIView,
            "get",
            "/search/",
            authenticated=True,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {"mobile": "This query parameter is required."},
        )

    def test_search_returns_404_for_unknown_mobile(self):
        response = self.call(
            UserSearchAPIView,
            "get",
            "/search/?mobile=09120000099",
            authenticated=True,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, "User not found.")

    def test_search_finds_user(self):
        response = self.call(
            UserSearchAPIView,
            "get",
            f"/search/?mobile={self.user.mobile}",
            authenticated=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["mobile"], self.user.mobile)
