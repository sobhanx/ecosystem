"""Tests for Location workspace drag-and-drop reorder endpoint."""

from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
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


class LocationReorderEndpointTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.client.force_login(self.user)
        self.footer = make_location("footer", name="Footer")
        self.a = quick_add_service(self.footer, "A", "https://a.example.com")
        self.b = quick_add_service(self.footer, "B", "https://b.example.com")
        self.c = quick_add_service(self.footer, "C", "https://c.example.com")
        self.reorder_url = reverse(
            "admin:ecosystem_location_reorder",
            args=[self.footer.pk],
        )
        self.workspace_url = reverse(
            "admin:ecosystem_location_workspace",
            args=[self.footer.pk],
        )

    def _post_json(self, url: str, payload, *, user=None):
        if user is not None:
            self.client.force_login(user)
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_reorder_success_updates_positions(self) -> None:
        response = self._post_json(
            self.reorder_url,
            {"ordered_ids": [self.c.pk, self.a.pk, self.b.pk]},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        self.c.refresh_from_db()
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual(self.c.position, 0)
        self.assertEqual(self.a.position, 1)
        self.assertEqual(self.b.position, 2)

    def test_reorder_permission_denied(self) -> None:
        User = get_user_model()
        limited = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="password",
            is_staff=True,
        )
        response = self._post_json(
            self.reorder_url,
            {"ordered_ids": [self.b.pk, self.a.pk, self.c.pk]},
            user=limited,
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data["ok"])

        self.a.refresh_from_db()
        self.assertEqual(self.a.position, 0)

    def test_reorder_rejects_ids_from_other_location(self) -> None:
        header = make_location("header")
        other = quick_add_service(header, "Other", "https://other.example.com")
        response = self._post_json(
            self.reorder_url,
            {"ordered_ids": [self.a.pk, self.b.pk, other.pk]},
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertIn("error", data)

        positions = list(
            Service.objects.filter(location=self.footer)
            .order_by("position")
            .values_list("pk", flat=True)
        )
        self.assertEqual(positions, [self.a.pk, self.b.pk, self.c.pk])

    def test_reorder_rejects_missing_ids(self) -> None:
        response = self._post_json(
            self.reorder_url,
            {"ordered_ids": [self.a.pk, self.b.pk]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_reorder_rejects_duplicate_ids(self) -> None:
        response = self._post_json(
            self.reorder_url,
            {"ordered_ids": [self.a.pk, self.a.pk, self.b.pk]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_reorder_rejects_malformed_payload(self) -> None:
        response = self.client.post(
            self.reorder_url,
            data="{not-json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

        response = self._post_json(self.reorder_url, {"ordered_ids": "nope"})
        self.assertEqual(response.status_code, 400)

        response = self._post_json(
            self.reorder_url,
            {"ordered_ids": [self.a.pk, "x", self.c.pk]},
        )
        self.assertEqual(response.status_code, 400)

    def test_reorder_rejects_get(self) -> None:
        response = self.client.get(self.reorder_url)
        self.assertEqual(response.status_code, 405)

    def test_workspace_template_includes_sortable_assets(self) -> None:
        response = self.client.get(self.workspace_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ecosystem/vendor/Sortable.min.js")
        self.assertContains(response, "ecosystem/workspace_sortable.js")
        self.assertContains(response, 'id="eco-sortable-services"')
        self.assertContains(response, 'data-service-id="%s"' % self.a.pk)
        self.assertContains(response, "eco-drag-handle")
        self.assertContains(response, self.reorder_url)
        self.assertContains(response, 'value="move_up"')
        self.assertContains(response, 'value="move_down"')
        self.assertContains(response, 'value="move_top"')
        self.assertContains(response, 'value="move_bottom"')

    def test_staff_with_change_permission_can_reorder(self) -> None:
        User = get_user_model()
        editor = User.objects.create_user(
            username="editor",
            email="editor@example.com",
            password="password",
            is_staff=True,
        )
        perm = Permission.objects.get(codename="change_location")
        editor.user_permissions.add(perm)
        response = self._post_json(
            self.reorder_url,
            {"ordered_ids": [self.b.pk, self.c.pk, self.a.pk]},
            user=editor,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.b.refresh_from_db()
        self.assertEqual(self.b.position, 0)
