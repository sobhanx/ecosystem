"""Tests for the Location workspace Admin view."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ecosystem.models import Location, Service
from ecosystem.services import quick_add_service


def make_location(key: str, **kwargs) -> Location:
    defaults = {
        "name": kwargs.pop("name", key.replace("_", " ").title()),
        "active": True,
    }
    defaults.update(kwargs)
    return Location.objects.create(key=key, **defaults)


class LocationWorkspaceTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.client.force_login(self.user)
        self.footer = make_location("footer", name="Footer")
        self.workspace_url = reverse(
            "admin:ecosystem_location_workspace",
            args=[self.footer.pk],
        )

    def test_workspace_get_renders_header_and_empty_state(self) -> None:
        response = self.client.get(self.workspace_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Footer")
        self.assertContains(response, "footer")
        self.assertContains(response, '{% ecosystem "footer" %}')
        self.assertContains(response, "Location workspace")
        self.assertContains(response, "Quick add")
        self.assertContains(response, "Copy tag")
        self.assertContains(response, "has no services yet")
        self.assertContains(response, "ecosystem/admin_copy.js")

    def test_quick_add_creates_service(self) -> None:
        response = self.client.post(
            self.workspace_url,
            {
                "workspace_action": "quick_add",
                "name": "Academy",
                "url": "https://academy.example.com",
            },
        )
        self.assertEqual(response.status_code, 302)
        service = Service.objects.get(location=self.footer)
        self.assertEqual(service.name, "Academy")
        self.assertEqual(service.position, 0)
        self.assertTrue(service.active)

    def test_nudge_and_toggle_actions(self) -> None:
        academy = quick_add_service(
            self.footer, "Academy", "https://academy.example.com"
        )
        shop = quick_add_service(self.footer, "Shop", "https://shop.example.com")

        self.client.post(
            self.workspace_url,
            {"workspace_action": "move_up", "service_id": shop.pk},
        )
        shop.refresh_from_db()
        academy.refresh_from_db()
        self.assertEqual(shop.position, 0)
        self.assertEqual(academy.position, 1)

        self.client.post(
            self.workspace_url,
            {"workspace_action": "toggle_active", "service_id": shop.pk},
        )
        shop.refresh_from_db()
        self.assertFalse(shop.active)

        self.client.post(
            self.workspace_url,
            {"workspace_action": "duplicate", "service_id": academy.pk},
        )
        self.assertEqual(Service.objects.filter(location=self.footer).count(), 3)

        self.client.post(
            self.workspace_url,
            {"workspace_action": "delete", "service_id": academy.pk},
        )
        self.assertFalse(Service.objects.filter(pk=academy.pk).exists())
        positions = list(
            Service.objects.filter(location=self.footer)
            .order_by("position")
            .values_list("position", flat=True)
        )
        self.assertEqual(positions, [0, 1])

    def test_workspace_rejects_service_from_other_location(self) -> None:
        header = make_location("header")
        other = quick_add_service(header, "Search", "https://search.example.com")
        response = self.client.post(
            self.workspace_url,
            {"workspace_action": "move_up", "service_id": other.pk},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "does not belong to this location")

    def test_bulk_activate_deactivate_duplicate(self) -> None:
        a = quick_add_service(self.footer, "A", "https://a.example.com")
        b = quick_add_service(self.footer, "B", "https://b.example.com")
        c = quick_add_service(self.footer, "C", "https://c.example.com")

        self.client.post(
            self.workspace_url,
            {
                "workspace_action": "bulk_deactivate",
                "service_ids": [a.pk, b.pk],
            },
        )
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertFalse(a.active)
        self.assertFalse(b.active)

        self.client.post(
            self.workspace_url,
            {
                "workspace_action": "bulk_activate",
                "service_ids": [a.pk, b.pk],
            },
        )
        a.refresh_from_db()
        self.assertTrue(a.active)

        before = Service.objects.filter(location=self.footer).count()
        self.client.post(
            self.workspace_url,
            {
                "workspace_action": "bulk_duplicate",
                "service_ids": [a.pk, c.pk],
            },
        )
        self.assertEqual(
            Service.objects.filter(location=self.footer).count(),
            before + 2,
        )

    def test_bulk_move_to_another_location(self) -> None:
        header = make_location("header", name="Header")
        a = quick_add_service(self.footer, "A", "https://a.example.com")
        b = quick_add_service(self.footer, "B", "https://b.example.com")
        response = self.client.post(
            self.workspace_url,
            {
                "workspace_action": "bulk_move",
                "service_ids": [a.pk, b.pk],
                "target_location": header.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(a.location_id, header.pk)
        self.assertEqual(b.location_id, header.pk)
        self.assertEqual(Service.objects.filter(location=self.footer).count(), 0)

    def test_bulk_requires_selection(self) -> None:
        quick_add_service(self.footer, "A", "https://a.example.com")
        response = self.client.post(
            self.workspace_url,
            {"workspace_action": "bulk_activate"},
            follow=True,
        )
        self.assertContains(response, "Select at least one service")

    def test_workspace_list_ui_includes_bulk_and_row_helpers(self) -> None:
        service = quick_add_service(
            self.footer, "Academy", "https://academy.example.com"
        )
        response = self.client.get(self.workspace_url)
        self.assertContains(response, "With selected")
        self.assertContains(response, 'name="service_ids"')
        self.assertContains(response, "bulk_activate")
        self.assertContains(response, "Copy URL")
        self.assertContains(response, "eco-logo-fallback")
        self.assertContains(response, 'data-copy="%s"' % service.url)
        self.assertContains(response, "1 active")
