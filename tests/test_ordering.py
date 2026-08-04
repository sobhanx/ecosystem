"""Ordering invariant tests for dense Service.position per Location."""

from __future__ import annotations

from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from ecosystem.admin import ServiceAdmin
from ecosystem.forms import ServiceAdminForm
from ecosystem.models import Location, Service
from ecosystem.services import (
    delete_service,
    delete_services,
    quick_add_service,
    reorder_services,
)


def make_location(key: str, **kwargs) -> Location:
    defaults = {
        "name": kwargs.pop("name", key.replace("_", " ").title()),
        "active": True,
    }
    defaults.update(kwargs)
    return Location.objects.create(key=key, **defaults)


def assert_dense_positions(testcase: TestCase, location: Location) -> list[Service]:
    """Assert services for ``location`` use positions ``0..n-1`` with no gaps."""
    services = list(
        Service.objects.filter(location=location).order_by("position", "pk")
    )
    positions = [service.position for service in services]
    testcase.assertEqual(
        positions,
        list(range(len(services))),
        f"Expected dense positions for {location.key!r}, got {positions}",
    )
    return services


class DeleteOrderingTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer")
        self.a = quick_add_service(self.footer, "A", "https://a.example.com")
        self.b = quick_add_service(self.footer, "B", "https://b.example.com")
        self.c = quick_add_service(self.footer, "C", "https://c.example.com")

    def test_delete_middle_service_renumbers(self) -> None:
        delete_service(self.b)
        remaining = assert_dense_positions(self, self.footer)
        self.assertEqual([s.name for s in remaining], ["A", "C"])

    def test_delete_last_service_keeps_prefix_dense(self) -> None:
        delete_service(self.c)
        remaining = assert_dense_positions(self, self.footer)
        self.assertEqual([s.name for s in remaining], ["A", "B"])

    def test_delete_only_service_leaves_empty(self) -> None:
        solo_location = make_location("solo")
        only = quick_add_service(solo_location, "Only", "https://only.example.com")
        delete_service(only)
        assert_dense_positions(self, solo_location)
        self.assertEqual(Service.objects.filter(location=solo_location).count(), 0)

    def test_delete_services_bulk_renumbers_each_location(self) -> None:
        header = make_location("header")
        h1 = quick_add_service(header, "H1", "https://h1.example.com")
        quick_add_service(header, "H2", "https://h2.example.com")
        deleted = delete_services([self.a, self.c, h1])
        self.assertEqual(deleted, 3)
        assert_dense_positions(self, self.footer)
        assert_dense_positions(self, header)
        self.assertEqual(
            list(
                Service.objects.filter(location=self.footer).values_list(
                    "name", flat=True
                )
            ),
            ["B"],
        )


class ServiceAdminOrderingTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.admin = ServiceAdmin(Service, site)
        self.footer = make_location("footer")
        self.header = make_location("header")
        self.a = quick_add_service(self.footer, "A", "https://a.example.com")
        self.b = quick_add_service(self.footer, "B", "https://b.example.com")
        self.c = quick_add_service(self.footer, "C", "https://c.example.com")

    def _request(self):
        request = RequestFactory().post("/")
        request.user = self.user
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))
        return request

    def test_position_excluded_from_admin_form(self) -> None:
        form = ServiceAdminForm()
        self.assertNotIn("position", form.fields)
        self.assertIn("position", self.admin.readonly_fields)

    def test_delete_model_renumbers_siblings(self) -> None:
        self.admin.delete_model(self._request(), self.b)
        remaining = assert_dense_positions(self, self.footer)
        self.assertEqual([s.name for s in remaining], ["A", "C"])

    def test_delete_queryset_renumbers_siblings(self) -> None:
        self.admin.delete_queryset(
            self._request(),
            Service.objects.filter(pk__in=[self.a.pk, self.c.pk]),
        )
        remaining = assert_dense_positions(self, self.footer)
        self.assertEqual([s.name for s in remaining], ["B"])

    def test_move_location_preserves_dense_positions(self) -> None:
        form = ServiceAdminForm(
            data={
                "name": self.b.name,
                "url": self.b.url,
                "location": self.header.pk,
                "description": "",
                "slug": self.b.slug,
                "active": True,
                "open_in_new_tab": True,
            },
            instance=self.b,
        )
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save(commit=False)
        self.admin.save_model(self._request(), obj, form, change=True)

        assert_dense_positions(self, self.footer)
        assert_dense_positions(self, self.header)
        self.b.refresh_from_db()
        self.assertEqual(self.b.location_id, self.header.pk)
        self.assertEqual(self.b.position, 0)


class WorkspaceDeleteOrderingTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.footer = make_location("footer")
        self.a = quick_add_service(self.footer, "A", "https://a.example.com")
        self.b = quick_add_service(self.footer, "B", "https://b.example.com")
        self.c = quick_add_service(self.footer, "C", "https://c.example.com")
        self.workspace_url = reverse(
            "admin:ecosystem_location_workspace",
            args=[self.footer.pk],
        )

    def test_workspace_delete_middle_keeps_dense_positions(self) -> None:
        response = self.client.post(
            self.workspace_url,
            {"workspace_action": "delete", "service_id": self.b.pk},
        )
        self.assertEqual(response.status_code, 302)
        remaining = assert_dense_positions(self, self.footer)
        self.assertEqual([s.name for s in remaining], ["A", "C"])


class ReorderCorruptionTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer")
        self.header = make_location("header")
        self.a = quick_add_service(self.footer, "A", "https://a.example.com")
        self.b = quick_add_service(self.footer, "B", "https://b.example.com")
        self.c = quick_add_service(self.footer, "C", "https://c.example.com")
        self.other = quick_add_service(
            self.header, "Other", "https://other.example.com"
        )

    def test_duplicate_ordered_ids_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            reorder_services(
                self.footer,
                [self.a.pk, self.a.pk, self.b.pk],
            )
        assert_dense_positions(self, self.footer)

    def test_missing_ids_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            reorder_services(self.footer, [self.a.pk, self.b.pk])
        assert_dense_positions(self, self.footer)

    def test_wrong_location_ids_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            reorder_services(
                self.footer,
                [self.a.pk, self.b.pk, self.other.pk],
            )
        assert_dense_positions(self, self.footer)

    def test_quick_add_rejects_explicit_position(self) -> None:
        with self.assertRaises(ValidationError):
            quick_add_service(
                self.footer,
                "X",
                "https://x.example.com",
                position=99,
            )
        assert_dense_positions(self, self.footer)
