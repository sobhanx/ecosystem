"""Domain-boundary tests for lookups/services and admin orchestration."""

from __future__ import annotations

from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from ecosystem.admin import LocationAdmin
from ecosystem.forms import ServiceAdminForm
from ecosystem.lookups import (
    get_location_by_key,
    get_location_services_by_ids,
    get_service_for_location,
    get_services_for_location,
)
from ecosystem.models import Location, Service
from ecosystem.services import (
    get_active_services,
    quick_add_service,
    set_locations_active,
)


def make_location(key: str, **kwargs) -> Location:
    defaults = {
        "name": kwargs.pop("name", key.replace("_", " ").title()),
        "active": True,
    }
    defaults.update(kwargs)
    return Location.objects.create(key=key, **defaults)


class LookupBoundaryTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer")
        self.header = make_location("header", active=False)
        self.a = quick_add_service(self.footer, "A", "https://a.example.com")
        self.b = quick_add_service(self.footer, "B", "https://b.example.com")

    def test_get_location_by_key_resolves_active_only(self) -> None:
        self.assertEqual(get_location_by_key("footer"), self.footer)
        self.assertIsNone(get_location_by_key("header"))
        self.assertIsNone(get_location_by_key("missing"))
        self.assertIsNone(get_location_by_key("  "))

    def test_get_services_for_location_orders_canonically(self) -> None:
        services = list(get_services_for_location(self.footer))
        self.assertEqual(services, [self.a, self.b])

    def test_get_service_for_location_scopes_to_location(self) -> None:
        self.assertEqual(
            get_service_for_location(self.footer, self.a.pk),
            self.a,
        )
        other = quick_add_service(
            make_location("other"), "X", "https://x.example.com"
        )
        self.assertIsNone(get_service_for_location(self.footer, other.pk))

    def test_get_location_services_by_ids(self) -> None:
        found = get_location_services_by_ids(self.footer, [self.b.pk, self.a.pk])
        self.assertEqual(found, [self.a, self.b])

    def test_services_module_still_reexports_get_active_services(self) -> None:
        from ecosystem import lookups
        from ecosystem import services

        self.assertIs(services.get_active_services, lookups.get_active_services)
        self.assertEqual(list(get_active_services("footer")), [self.a, self.b])


class LocationWriteBoundaryTests(TestCase):
    def test_set_locations_active(self) -> None:
        footer = make_location("footer")
        header = make_location("header")
        updated = set_locations_active(
            Location.objects.filter(pk__in=[footer.pk, header.pk]),
            False,
        )
        self.assertEqual(updated, 2)
        footer.refresh_from_db()
        header.refresh_from_db()
        self.assertFalse(footer.active)
        self.assertFalse(header.active)

    def test_location_admin_actions_use_service_layer(self) -> None:
        User = get_user_model()
        user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        admin = LocationAdmin(Location, site)
        footer = make_location("footer")
        request = RequestFactory().post("/")
        request.user = user
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))
        admin.deactivate_locations(
            request,
            Location.objects.filter(pk=footer.pk),
        )
        footer.refresh_from_db()
        self.assertFalse(footer.active)


class SlugHelperBoundaryTests(TestCase):
    def test_form_and_model_share_slug_builder(self) -> None:
        location = make_location("footer")
        Service.objects.create(
            name="Shop",
            slug="shop",
            url="https://shop.example.com",
            location=location,
            position=0,
        )
        form = ServiceAdminForm(
            data={
                "name": "Shop",
                "url": "https://shop-2.example.com",
                "location": location.pk,
                "description": "",
                "slug": "",
                "active": True,
                "open_in_new_tab": True,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["slug"], "shop-2")
        self.assertEqual(
            Service.build_unique_slug("Shop"),
            "shop-2",
        )
