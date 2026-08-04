"""Demo project i18n activation checks for Persian Admin."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from django.test import SimpleTestCase
from django.utils import translation
from django.utils.translation import gettext as _


DEMO_ROOT = Path(__file__).resolve().parents[1] / "demo"


class DemoPersianAdminActivationTests(SimpleTestCase):
    """
    Persian catalogs already exist; Admin stays English unless the host
    activates language ``fa``. The demo project is the product laboratory.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # Import demo settings as a plain module (not Django settings).
        sys.path.insert(0, str(DEMO_ROOT))
        cls.demo_settings = importlib.import_module("config.settings")

    def test_demo_enables_persian_as_default_language(self) -> None:
        self.assertTrue(self.demo_settings.USE_I18N)
        self.assertEqual(self.demo_settings.LANGUAGE_CODE, "fa")
        self.assertIn(
            "django.middleware.locale.LocaleMiddleware",
            self.demo_settings.MIDDLEWARE,
        )
        session_idx = self.demo_settings.MIDDLEWARE.index(
            "django.contrib.sessions.middleware.SessionMiddleware"
        )
        locale_idx = self.demo_settings.MIDDLEWARE.index(
            "django.middleware.locale.LocaleMiddleware"
        )
        self.assertGreater(locale_idx, session_idx)
        self.assertIn(("fa", "Persian"), self.demo_settings.LANGUAGES)

    def test_persian_catalog_translates_ecosystem_and_django_admin_strings(
        self,
    ) -> None:
        with translation.override("fa"):
            self.assertEqual(_("Ecosystem"), "اکوسیستم")
            self.assertEqual(_("location"), "محل نمایش")
            self.assertEqual(_("Workspace"), "مدیریت سرویس‌های محل نمایش")
            # Django's own Admin catalog (proves host fa locale is available).
            self.assertNotEqual(_("Add"), "Add")
            self.assertNotEqual(_("Log in"), "Log in")
