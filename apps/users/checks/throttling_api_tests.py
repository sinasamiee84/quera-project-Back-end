from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.settings import api_settings
from rest_framework.test import APITestCase

from apps.users.api.throttles import AuthRateThrottle
from apps.users.api.views import LoginAPIView, RegisterAPIView
from apps.users.models import User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ThrottlingAPIChecks(APITestCase):
    def setUp(self):
        # خالی کردن کش تراتل قبل از هر تست
        cache.clear()

        self.email = "throttle_test@example.com"
        self.mobile = "09121234567"
        self.password = "TestPass1234!"

        # ساخت کاربر تستی با شماره موبایل و پسورد معتبر
        self.user = User.objects.create_user(
            email=self.email,
            mobile=self.mobile,
            password=self.password,
        )

        self.login_url = reverse("api-users:login")

    def test_auth_throttle_scope_is_auth(self):
        """بررسی اینکه کلاس AuthRateThrottle دارای scope برابر auth باشد"""
        throttle = AuthRateThrottle()
        self.assertEqual(throttle.scope, "auth")

    def test_register_view_uses_auth_throttle(self):
        """بررسی اینکه ویوی ثبت‌نام حتما کلاس AuthRateThrottle را دارا باشد"""
        self.assertIn(AuthRateThrottle, RegisterAPIView.throttle_classes)

    def test_login_view_uses_auth_throttle(self):
        """بررسی اینکه ویوی ورود حتما کلاس AuthRateThrottle را دارا باشد"""
        self.assertIn(AuthRateThrottle, LoginAPIView.throttle_classes)

    def test_auth_throttle_rate_is_configured(self):
        """بررسی وجود تنظیم نرخ auth در DEFAULT_THROTTLE_RATES و برابر بودن آن با 10/minute"""
        rates = api_settings.DEFAULT_THROTTLE_RATES
        self.assertIn("auth", rates)
        self.assertEqual(rates["auth"], "10/minute")

    def test_login_is_throttled_after_limit(self):
        """ارسال ۱۰ درخواست مجاز اول و بررسی دریافت پاسخ 429 در درخواست یازدهم"""
        # دقت کن در فاز اول Quera Clock ورود بر اساس موبایل است یا ایمیل:
        # برای اطمینان هر دو فیلد فرستاده می‌شود
        login_data = {
            "mobile": self.mobile,
            "email": self.email,
            "password": self.password,
        }

        # ارسال ۱۰ درخواست مجاز اول
        for _ in range(10):
            response = self.client.post(self.login_url, login_data, format="json")
            self.assertNotEqual(
                response.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
                "درخواست‌های اول تا دهم نباید ۴۲۹ دریافت کنند.",
            )

        # درخواست یازدهم باید با کد 429 مسدود شود
        blocked_response = self.client.post(self.login_url, login_data, format="json")
        self.assertEqual(
            blocked_response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
            "درخواست یازدهم در یک دقیقه باید وضعیت ۴۲۹ برگرداند.",
        )
