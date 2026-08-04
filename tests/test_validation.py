"""Model and form validation tests for data integrity."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.template import Context, Template
from django.test import TestCase

from ecosystem.forms import ServiceAdminForm, WorkspaceQuickAddForm
from ecosystem.lookups import get_active_services
from ecosystem.models import Location, Service
from ecosystem.services import quick_add_service
from tests.helpers import make_location


class LocationValidationTests(TestCase):
    def test_whitespace_only_key_fails_clean(self) -> None:
        location = Location(key="   ", name="Footer")
        with self.assertRaises(ValidationError) as ctx:
            location.full_clean()
        self.assertIn("key", ctx.exception.message_dict)

    def test_blank_key_fails_clean(self) -> None:
        location = Location(key="", name="Footer")
        with self.assertRaises(ValidationError) as ctx:
            location.full_clean()
        self.assertIn("key", ctx.exception.message_dict)

    def test_key_is_normalized_by_clean(self) -> None:
        location = Location(key="  footer  ", name="  Footer  ")
        location.full_clean()
        self.assertEqual(location.key, "footer")
        self.assertEqual(location.name, "Footer")

    def test_key_is_normalized_on_save(self) -> None:
        location = make_location("  docs_nav  ", name="Docs")
        self.assertEqual(location.key, "docs_nav")

    def test_blank_name_falls_back_to_key_on_clean(self) -> None:
        location = Location(key="header", name="   ")
        location.full_clean()
        self.assertEqual(location.name, "header")

    def test_unique_key_rejected(self) -> None:
        make_location("footer")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_location("footer", name="Other")


class ServiceValidationTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer")

    def test_slug_generation_uses_canonical_helper(self) -> None:
        Service.objects.create(
            name="Shop",
            slug="shop",
            url="https://shop.example.com",
            location=self.footer,
            position=0,
        )
        expected = Service.build_unique_slug("Shop")
        form = ServiceAdminForm(
            data={
                "name": "Shop",
                "url": "https://shop-2.example.com",
                "location": self.footer.pk,
                "description": "",
                "slug": "",
                "active": True,
                "open_in_new_tab": True,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["slug"], expected)
        self.assertEqual(expected, "shop-2")

    def test_slug_whitespace_normalized_on_save(self) -> None:
        service = Service(
            name="Academy",
            slug="  academy  ",
            url="https://academy.example.com",
            location=self.footer,
            position=0,
        )
        service.save()
        service.refresh_from_db()
        self.assertEqual(service.slug, "academy")

    def test_admin_form_excludes_position(self) -> None:
        form = ServiceAdminForm()
        self.assertNotIn("position", form.fields)

    def test_invalid_url_rejected_consistently(self) -> None:
        admin_form = ServiceAdminForm(
            data={
                "name": "Broken",
                "url": "not-a-url",
                "location": self.footer.pk,
                "description": "",
                "slug": "broken",
                "active": True,
                "open_in_new_tab": True,
            }
        )
        self.assertFalse(admin_form.is_valid())
        self.assertIn("url", admin_form.errors)

        quick = WorkspaceQuickAddForm(
            data={"name": "Broken", "url": "not-a-url"}
        )
        self.assertFalse(quick.is_valid())
        self.assertIn("url", quick.errors)


class TemplateApiRegressionTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer")
        self.active_first = quick_add_service(
            self.footer, "Shop", "https://shop.example.com"
        )
        self.inactive = quick_add_service(
            self.footer, "Hidden", "https://hidden.example.com", active=False
        )
        self.active_second = quick_add_service(
            self.footer, "Blog", "https://blog.example.com"
        )

    def test_ecosystem_tag_still_renders(self) -> None:
        rendered = Template(
            '{% load ecosystem %}{% ecosystem "footer" %}'
        ).render(Context())
        self.assertIn("Shop", rendered)
        self.assertIn("https://shop.example.com", rendered)
        self.assertIn("Blog", rendered)
        self.assertNotIn("Hidden", rendered)
        self.assertNotIn("https://hidden.example.com", rendered)

    def test_missing_location_returns_empty(self) -> None:
        self.assertEqual(list(get_active_services("missing")), [])

    def test_inactive_location_returns_empty(self) -> None:
        self.footer.active = False
        self.footer.save(update_fields=["active"])
        self.assertEqual(list(get_active_services("footer")), [])

    def test_inactive_services_excluded(self) -> None:
        services = list(get_active_services("footer"))
        self.assertEqual(
            [service.name for service in services],
            ["Shop", "Blog"],
        )

    def test_ordering_follows_position(self) -> None:
        services = list(get_active_services("footer"))
        self.assertEqual(
            [service.pk for service in services],
            [self.active_first.pk, self.active_second.pk],
        )
        # Inactive service still occupies position 1 in the location list.
        self.assertEqual([service.position for service in services], [0, 2])
