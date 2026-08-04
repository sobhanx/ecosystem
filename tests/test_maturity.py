"""Testing-maturity coverage for permissions, services, and observable behavior."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from ecosystem.models import Location, Service
from ecosystem.services import (
    delete_services,
    duplicate_services,
    move_services,
    quick_add_service,
    set_services_active,
)
from tests.helpers import assert_dense_positions, make_location


class WorkspacePermissionMaturityTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer", name="Footer")
        self.service = quick_add_service(
            self.footer, "Shop", "https://shop.example.com"
        )
        self.workspace_url = reverse(
            "admin:ecosystem_location_workspace",
            args=[self.footer.pk],
        )

    def test_anonymous_user_cannot_access_workspace(self) -> None:
        response = Client().get(self.workspace_url)
        self.assertIn(response.status_code, (302, 403))
        if response.status_code == 302:
            self.assertIn("/login", response.url)

    def test_staff_without_change_cannot_mutate_workspace(self) -> None:
        User = get_user_model()
        limited = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="password",
            is_staff=True,
        )
        client = Client()
        client.force_login(limited)
        response = client.post(
            self.workspace_url,
            {
                "workspace_action": "quick_add",
                "name": "Blog",
                "url": "https://blog.example.com",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Service.objects.filter(location=self.footer).count(), 1)

    def test_staff_with_change_permission_can_access_workspace(self) -> None:
        User = get_user_model()
        editor = User.objects.create_user(
            username="editor",
            email="editor@example.com",
            password="password",
            is_staff=True,
        )
        content_type = ContentType.objects.get_for_model(Location)
        permission = Permission.objects.get(
            content_type=content_type,
            codename="change_location",
        )
        editor.user_permissions.add(permission)
        # Viewing workspace also needs view/change; Django Admin typically
        # requires change for custom admin_view mutations. Change is enough
        # for has_change_permission.
        client = Client()
        client.force_login(editor)
        response = client.get(self.workspace_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Footer")
        self.assertContains(response, "Shop")
        self.assertContains(response, '{% ecosystem "footer" %}')


class ServiceLayerMaturityTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer")
        self.header = make_location("header")
        self.a = quick_add_service(self.footer, "A", "https://a.example.com")
        self.b = quick_add_service(self.footer, "B", "https://b.example.com")
        self.c = quick_add_service(self.footer, "C", "https://c.example.com")

    def test_duplicate_services_appends_copies_densely(self) -> None:
        copies = duplicate_services([self.a, self.c])
        self.assertEqual(len(copies), 2)
        remaining = assert_dense_positions(self, self.footer)
        self.assertEqual(len(remaining), 5)
        self.assertEqual(
            [service.name for service in remaining],
            ["A", "B", "C", "A", "C"],
        )
        self.assertEqual(copies[0].url, self.a.url)
        self.assertEqual(copies[1].url, self.c.url)
        self.assertNotEqual(copies[0].pk, self.a.pk)

    def test_move_services_empty_is_noop(self) -> None:
        self.assertEqual(move_services([], self.header), [])
        assert_dense_positions(self, self.footer)
        assert_dense_positions(self, self.header)

    def test_delete_services_empty_is_noop(self) -> None:
        self.assertEqual(delete_services([]), 0)
        assert_dense_positions(self, self.footer)

    def test_set_services_active_preserves_positions(self) -> None:
        set_services_active([self.a, self.c], False)
        assert_dense_positions(self, self.footer)
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.c.refresh_from_db()
        self.assertFalse(self.a.active)
        self.assertTrue(self.b.active)
        self.assertFalse(self.c.active)
