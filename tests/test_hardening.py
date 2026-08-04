"""Hardening-focused Admin and fixture tests for Ecosystem 2.1."""

from __future__ import annotations

import json
from pathlib import Path

from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from ecosystem.admin import ServiceAdmin
from ecosystem.forms import ServiceAdminForm
from ecosystem.models import Location, Service
from ecosystem.services import duplicate_service, quick_add_service


def make_location(key: str, **kwargs) -> Location:
    defaults = {
        "name": kwargs.pop("name", key.replace("_", " ").title()),
        "active": True,
    }
    defaults.update(kwargs)
    return Location.objects.create(key=key, **defaults)


class ServiceAdminLocationMoveTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.admin = ServiceAdmin(Service, site)
        self.footer = make_location("footer", name="Footer")
        self.header = make_location("header", name="Header")
        self.keep = quick_add_service(
            self.footer, "Keep", "https://keep.example.com"
        )
        self.mover = quick_add_service(
            self.footer, "Mover", "https://mover.example.com"
        )

    def _request(self):
        request = RequestFactory().post("/")
        request.user = self.user
        return request

    def test_changing_location_uses_move_services_and_renumbers(self) -> None:
        form = ServiceAdminForm(
            data={
                "name": self.mover.name,
                "url": self.mover.url,
                "location": self.header.pk,
                "description": "",
                "slug": self.mover.slug,
                "active": True,
                "open_in_new_tab": True,
            },
            instance=self.mover,
        )
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save(commit=False)
        self.admin.save_model(self._request(), obj, form, change=True)

        self.mover.refresh_from_db()
        self.keep.refresh_from_db()
        self.assertEqual(self.mover.location_id, self.header.pk)
        self.assertEqual(self.mover.position, 0)
        self.assertEqual(self.keep.location_id, self.footer.pk)
        self.assertEqual(self.keep.position, 0)

    def test_changelist_select_related_location(self) -> None:
        qs = self.admin.get_queryset(self._request())
        self.assertIn("location", qs.query.select_related)


class ReorderSecurityTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.footer = make_location("footer")
        self.a = quick_add_service(self.footer, "A", "https://a.example.com")
        self.b = quick_add_service(self.footer, "B", "https://b.example.com")
        self.reorder_url = reverse(
            "admin:ecosystem_location_reorder",
            args=[self.footer.pk],
        )
        self.workspace_url = reverse(
            "admin:ecosystem_location_workspace",
            args=[self.footer.pk],
        )

    def test_reorder_requires_csrf(self) -> None:
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(
            self.reorder_url,
            data=json.dumps({"ordered_ids": [self.b.pk, self.a.pk]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        workspace = client.get(self.workspace_url)
        self.assertEqual(workspace.status_code, 200)
        csrf = client.cookies.get("csrftoken")
        self.assertIsNotNone(csrf)
        response = client.post(
            self.reorder_url,
            data=json.dumps({"ordered_ids": [self.b.pk, self.a.pk]}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf.value,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_workspace_permission_denied_for_staff_without_change(self) -> None:
        User = get_user_model()
        limited = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="password",
            is_staff=True,
        )
        client = Client()
        client.force_login(limited)
        response = client.get(self.workspace_url)
        self.assertEqual(response.status_code, 403)


class DuplicateOrderingHardeningTests(TestCase):
    def test_sequential_duplicates_receive_dense_positions(self) -> None:
        footer = make_location("footer")
        original = quick_add_service(footer, "Shop", "https://shop.example.com")
        copies = [duplicate_service(original) for _ in range(3)]
        positions = list(
            Service.objects.filter(location=footer)
            .order_by("position", "pk")
            .values_list("position", flat=True)
        )
        self.assertEqual(positions, [0, 1, 2, 3])
        self.assertEqual([copy.position for copy in copies], [1, 2, 3])


class DemoFixtureTests(TestCase):
    def test_sample_services_fixture_loads(self) -> None:
        fixture = (
            Path(__file__).resolve().parents[1]
            / "demo"
            / "demoapp"
            / "fixtures"
            / "sample_services.json"
        )
        self.assertTrue(fixture.exists())
        call_command("loaddata", str(fixture), verbosity=0)
        self.assertTrue(Location.objects.filter(key="header").exists())
        self.assertTrue(Location.objects.filter(key="main").exists())
        self.assertTrue(Location.objects.filter(key="footer").exists())
        self.assertEqual(Service.objects.filter(location__key="header").count(), 3)
        self.assertTrue(
            Service.objects.filter(location__key="footer", name="Careers", active=False).exists()
        )
        from ecosystem.lookups import get_active_services

        footer_names = list(get_active_services("footer").values_list("name", flat=True))
        self.assertEqual(footer_names, ["Blog", "Status"])
        self.assertNotIn("Careers", footer_names)


class PersianWorkspaceTranslationTests(TestCase):
    def test_workspace_strings_have_persian_translations(self) -> None:
        with translation.override("fa"):
            self.assertEqual(
                _("Location workspace"),
                "مدیریت سرویس‌های محل نمایش",
            )
            self.assertEqual(_("Copy tag"), "کپی تگ")
            self.assertEqual(_("Open workspace"), "باز کردن مدیریت سرویس‌ها")
            self.assertEqual(_("Workspace"), "مدیریت سرویس‌های محل نمایش")
            self.assertEqual(_("location"), "محل نمایش")
            self.assertEqual(_("locations"), "محل‌های نمایش")
            self.assertEqual(_("service"), "سرویس")
            self.assertEqual(_("position"), "ترتیب")
            self.assertEqual(_("Order"), "ترتیب")
            self.assertEqual(
                _(
                    "Could not save order. Refresh the page and try again, "
                    "or use the move buttons."
                ),
                "ذخیره ترتیب ممکن نشد. صفحه را تازه کنید و دوباره تلاش کنید، "
                "یا از دکمه‌های جابه‌جایی استفاده کنید.",
            )
            self.assertEqual(
                _("Select at least one service."),
                "حداقل یک سرویس را انتخاب کنید.",
            )
            self.assertNotIn("display order", _("position").lower())
            self.assertNotEqual(_("Workspace"), "Workspace")
