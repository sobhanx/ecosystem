"""Demo Persian Admin activation — request lifecycle regressions."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.utils.translation import get_language, gettext as _
from django.utils import translation


DEMO_ROOT = Path(__file__).resolve().parents[1] / "demo"


class DemoPersianAdminActivationTests(SimpleTestCase):
    """Demo settings must keep Persian fixed for Admin HTTP requests."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        sys.path.insert(0, str(DEMO_ROOT))
        cls.demo_settings = importlib.reload(importlib.import_module("config.settings"))

    def test_demo_uses_fixed_persian_without_locale_middleware(self) -> None:
        self.assertTrue(self.demo_settings.USE_I18N)
        self.assertEqual(self.demo_settings.LANGUAGE_CODE, "fa")
        self.assertEqual(self.demo_settings.LANGUAGES, [("fa", "Persian")])
        self.assertNotIn(
            "django.middleware.locale.LocaleMiddleware",
            self.demo_settings.MIDDLEWARE,
        )

    def test_persian_catalog_translates_ecosystem_and_django_admin_strings(
        self,
    ) -> None:
        with translation.override("fa"):
            self.assertEqual(_("Ecosystem"), "اکوسیستم")
            self.assertEqual(_("location"), "محل نمایش")
            self.assertEqual(_("Workspace"), "مدیریت سرویس‌های محل نمایش")
            self.assertEqual(_("Add"), "اضافه کردن")
            self.assertEqual(_("Change"), "تغییر")
            self.assertEqual(_("Delete"), "حذف")


@override_settings(
    LANGUAGE_CODE="fa",
    LANGUAGES=[("fa", "Persian")],
    USE_I18N=True,
    MIDDLEWARE=[
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
    ],
    ROOT_URLCONF="tests.urls",
)
class AdminRequestLanguageTests(TestCase):
    """Admin HTTP requests must stay Persian even when the browser prefers English."""

    def setUp(self) -> None:
        translation.activate("fa")
        self.addCleanup(translation.deactivate)
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="fa-admin",
            email="fa@example.com",
            password="password",
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_admin_request_language_is_persian_despite_accept_language_en(self) -> None:
        response = self.client.get(
            "/admin/",
            HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_language(), "fa")
        body = response.content.decode()
        self.assertIn("اضافه کردن", body)
        self.assertNotIn(">Add<", body)

    def test_admin_changelist_uses_persian_ecosystem_labels(self) -> None:
        response = self.client.get(
            "/admin/ecosystem/location/",
            HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9",
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("محل", body)
        self.assertIn("اکوسیستم", body)
        self.assertNotIn(">Locations<", body)

    def test_template_tag_api_unchanged_under_persian(self) -> None:
        from ecosystem.models import Location, Service

        location = Location.objects.create(key="footer", name="Footer", active=True)
        Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location=location,
            position=0,
            active=True,
        )
        rendered = Template(
            '{% load ecosystem %}{% ecosystem "footer" %}'
        ).render(Context())
        self.assertIn("Shop", rendered)
        self.assertIn("https://shop.example.com", rendered)
