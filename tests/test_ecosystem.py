"""Tests for the ecosystem reusable application."""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.template import Context, Template
from django.test import SimpleTestCase, TestCase, override_settings

from ecosystem.models import Location, Service
from ecosystem.selectors import get_active_services
from ecosystem.services import get_active_services as get_active_services_compat


def make_location(key: str, **kwargs) -> Location:
    """Create a location with sensible defaults for tests."""
    defaults = {
        "name": kwargs.pop("name", key.replace("_", " ").title()),
        "active": True,
    }
    defaults.update(kwargs)
    return Location.objects.create(key=key, **defaults)


class LocationModelTests(TestCase):
    """Unit tests for the ``Location`` model."""

    def test_str_returns_name(self) -> None:
        location = Location(key="footer", name="Footer")
        self.assertEqual(str(location), "Footer")

    def test_key_is_stripped_on_save(self) -> None:
        location = make_location("  footer  ", name="Footer")
        self.assertEqual(location.key, "footer")

    def test_blank_name_falls_back_to_key(self) -> None:
        location = Location(key="header", name="   ")
        location.save()
        self.assertEqual(location.name, "header")

    def test_key_must_be_unique(self) -> None:
        make_location("footer")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_location("footer", name="Other Footer")


class ServiceModelTests(TestCase):
    """Unit tests for the ``Service`` model."""

    def setUp(self) -> None:
        self.footer = make_location("footer", name="Footer")
        self.header = make_location("header", name="Header")

    def test_str_returns_name(self) -> None:
        service = Service(
            name="Academy",
            url="https://academy.example.com",
            location=self.footer,
        )
        self.assertEqual(str(service), "Academy")

    def test_default_field_values(self) -> None:
        service = Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location=self.footer,
        )
        self.assertEqual(service.position, 0)
        self.assertTrue(service.active)
        self.assertTrue(service.open_in_new_tab)
        self.assertEqual(service.location_id, self.footer.pk)
        self.assertEqual(service.slug, "shop")
        self.assertEqual(service.description, "")

    def test_slug_is_generated_from_name_when_empty(self) -> None:
        service = Service.objects.create(
            name="My Academy",
            url="https://academy.example.com",
            location=self.header,
        )
        self.assertEqual(service.slug, "my-academy")

    def test_slug_is_not_regenerated_when_already_set(self) -> None:
        service = Service.objects.create(
            name="Academy",
            slug="custom-academy",
            url="https://academy.example.com",
            location=self.header,
        )
        service.name = "Renamed Academy"
        service.save()
        service.refresh_from_db()
        self.assertEqual(service.slug, "custom-academy")

    def test_slug_regenerates_only_when_cleared(self) -> None:
        service = Service.objects.create(
            name="Academy",
            slug="custom-academy",
            url="https://academy.example.com",
            location=self.header,
        )
        service.name = "Learning Hub"
        service.slug = ""
        service.save()
        service.refresh_from_db()
        self.assertEqual(service.slug, "learning-hub")

    def test_unique_slug_collision_gets_suffix(self) -> None:
        Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location=self.footer,
        )
        duplicate = Service.objects.create(
            name="Shop",
            url="https://shop-b.example.com",
            location=self.footer,
        )
        self.assertEqual(duplicate.slug, "shop-2")

    def test_slug_must_be_unique(self) -> None:
        Service.objects.create(
            name="Shop",
            slug="shop",
            url="https://shop.example.com",
            location=self.footer,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Service.objects.create(
                    name="Other Shop",
                    slug="shop",
                    url="https://other.example.com",
                    location=self.footer,
                )

    def test_description_is_optional(self) -> None:
        article = make_location("article_bottom")
        service = Service.objects.create(
            name="Blog",
            url="https://blog.example.com",
            location=article,
            description="Sibling blog for long-form content.",
        )
        self.assertEqual(
            service.description,
            "Sibling blog for long-form content.",
        )

    def test_meta_ordering_by_position_then_name(self) -> None:
        Service.objects.create(
            name="Zebra",
            url="https://zebra.example.com",
            location=self.header,
            position=2,
        )
        Service.objects.create(
            name="Alpha",
            url="https://alpha.example.com",
            location=self.header,
            position=1,
        )
        Service.objects.create(
            name="Beta",
            url="https://beta.example.com",
            location=self.header,
            position=1,
        )

        names = list(
            Service.objects.filter(location=self.header).values_list(
                "name", flat=True
            )
        )
        self.assertEqual(names, ["Alpha", "Beta", "Zebra"])


class ActiveServicesQueryTests(TestCase):
    """Tests for ``get_active_services`` filtering and ordering."""

    def setUp(self) -> None:
        self.footer = make_location("footer")
        self.header = make_location("header")
        self.footer_first = Service.objects.create(
            name="Blog",
            url="https://blog.example.com",
            location=self.footer,
            position=1,
            active=True,
        )
        self.footer_second = Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location=self.footer,
            position=2,
            active=True,
        )
        self.footer_inactive = Service.objects.create(
            name="Legacy",
            url="https://legacy.example.com",
            location=self.footer,
            position=0,
            active=False,
        )
        self.header_service = Service.objects.create(
            name="Academy",
            url="https://academy.example.com",
            location=self.header,
            position=0,
            active=True,
        )

    def test_only_active_services_returned(self) -> None:
        services = list(get_active_services("footer"))
        self.assertEqual(services, [self.footer_first, self.footer_second])
        self.assertNotIn(self.footer_inactive, services)

    def test_location_filtering(self) -> None:
        footer_services = list(get_active_services("footer"))
        header_services = list(get_active_services("header"))

        self.assertEqual(footer_services, [self.footer_first, self.footer_second])
        self.assertEqual(header_services, [self.header_service])

    def test_dynamic_location_keys(self) -> None:
        dashboard = make_location("dashboard_left")
        custom = Service.objects.create(
            name="Dashboard Widget",
            url="https://dashboard.example.com",
            location=dashboard,
            active=True,
        )
        services = list(get_active_services("dashboard_left"))
        self.assertEqual(services, [custom])
        self.assertEqual(list(get_active_services("missing_key")), [])

    def test_query_layer_strips_location_argument(self) -> None:
        docs = make_location("docs_nav")
        service = Service.objects.create(
            name="Docs Portal",
            url="https://docs.example.com",
            location=docs,
            active=True,
        )
        self.assertEqual(list(get_active_services("  docs_nav  ")), [service])

    def test_ordering_by_position_then_name(self) -> None:
        Service.objects.create(
            name="Docs",
            url="https://docs.example.com",
            location=self.footer,
            position=1,
            active=True,
        )
        names = list(
            get_active_services("footer").values_list("name", flat=True)
        )
        self.assertEqual(names, ["Blog", "Docs", "Shop"])

    def test_inactive_location_returns_empty(self) -> None:
        self.footer.active = False
        self.footer.save(update_fields=["active"])
        self.assertEqual(list(get_active_services("footer")), [])

    def test_services_module_reexports_selector(self) -> None:
        self.assertIs(get_active_services_compat, get_active_services)


class EcosystemTemplateTagTests(TestCase):
    """Tests for the ``ecosystem`` inclusion tag and legacy alias."""

    def setUp(self) -> None:
        self.footer = make_location("footer")
        self.header = make_location("header")
        Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location=self.footer,
            position=1,
            active=True,
            open_in_new_tab=True,
        )
        Service.objects.create(
            name="Inactive Footer",
            url="https://inactive.example.com",
            location=self.footer,
            position=0,
            active=False,
        )
        Service.objects.create(
            name="Header Only",
            url="https://header.example.com",
            location=self.header,
            position=0,
            active=True,
        )

    def test_ecosystem_tag_renders_active_location_services(self) -> None:
        rendered = Template(
            "{% load ecosystem %}{% ecosystem 'footer' %}"
        ).render(Context())

        self.assertIn("Shop", rendered)
        self.assertIn("https://shop.example.com", rendered)
        self.assertIn('target="_blank"', rendered)
        self.assertIn('rel="noopener noreferrer"', rendered)
        self.assertNotIn("Inactive Footer", rendered)
        self.assertNotIn("Header Only", rendered)

    def test_legacy_ecosystem_services_alias_still_works(self) -> None:
        rendered = Template(
            "{% load ecosystem %}{% ecosystem_services 'footer' %}"
        ).render(Context())
        self.assertIn("Shop", rendered)

    def test_template_tag_respects_open_in_new_tab_false(self) -> None:
        sidebar = make_location("sidebar")
        Service.objects.create(
            name="Same Tab",
            url="https://same.example.com",
            location=sidebar,
            active=True,
            open_in_new_tab=False,
        )
        rendered = Template(
            "{% load ecosystem %}{% ecosystem 'sidebar' %}"
        ).render(Context())

        self.assertIn("Same Tab", rendered)
        self.assertNotIn('target="_blank"', rendered)
        self.assertNotIn("noopener noreferrer", rendered)

    def test_template_tag_empty_location_renders_empty_list(self) -> None:
        rendered = Template(
            "{% load ecosystem %}{% ecosystem 'custom' %}"
        ).render(Context())

        self.assertIn('<ul class="ecosystem-services">', rendered)
        self.assertNotIn("<li", rendered)

    def test_template_tag_accepts_arbitrary_location(self) -> None:
        pricing = make_location("pricing_page")
        Service.objects.create(
            name="Pricing",
            url="https://shop.example.com/pricing",
            location=pricing,
            active=True,
        )
        rendered = Template(
            "{% load ecosystem %}{% ecosystem 'pricing_page' %}"
        ).render(Context())
        self.assertIn("Pricing", rendered)


@override_settings(ROOT_URLCONF="ecosystem.urls")
class EcosystemUrlsTests(SimpleTestCase):
    """Ensure the app exposes a valid, empty URLConf."""

    def test_urlpatterns_is_empty(self) -> None:
        from ecosystem.urls import app_name, urlpatterns

        self.assertEqual(app_name, "ecosystem")
        self.assertEqual(urlpatterns, [])


class ServiceAdminFormTests(TestCase):
    """Tests for ServiceAdminForm against the Location FK."""

    def test_form_uses_location_model_choice(self) -> None:
        from ecosystem.forms import ServiceAdminForm

        footer = make_location("footer", name="Footer")
        form = ServiceAdminForm()
        self.assertIn(footer, form.fields["location"].queryset)
        self.assertEqual(str(form.fields["location"].label), "Placement")


class ServiceAdminTests(TestCase):
    """Tests for ServiceAdmin list actions and logo rendering."""

    def setUp(self) -> None:
        from django.contrib.admin.sites import site
        from django.contrib.auth import get_user_model

        from ecosystem.admin import ServiceAdmin

        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.admin = ServiceAdmin(Service, site)
        self.footer = make_location("footer")

    def test_activate_and_deactivate_actions(self) -> None:
        active = Service.objects.create(
            name="Active",
            url="https://active.example.com",
            location=self.footer,
            active=True,
        )
        inactive = Service.objects.create(
            name="Inactive",
            url="https://inactive.example.com",
            location=self.footer,
            active=False,
        )

        self.admin.deactivate_services(
            request=self._request(),
            queryset=Service.objects.filter(pk=active.pk),
        )
        active.refresh_from_db()
        self.assertFalse(active.active)

        self.admin.activate_services(
            request=self._request(),
            queryset=Service.objects.filter(pk=inactive.pk),
        )
        inactive.refresh_from_db()
        self.assertTrue(inactive.active)

    def test_logo_preview_without_logo_is_dash(self) -> None:
        service = Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location=self.footer,
        )
        self.assertEqual(self.admin.logo_preview(service), "—")
        self.assertEqual(self.admin.logo_thumbnail(service), "—")

    def test_logo_preview_with_image(self) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        service = Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location=self.footer,
            logo=SimpleUploadedFile("logo.png", png, content_type="image/png"),
        )
        html = self.admin.logo_preview(service)
        self.assertIn("<img", html)
        self.assertIn("ecosystem/services/", html)
        self.assertIn("object-fit:contain", html)

    def test_admin_list_configuration(self) -> None:
        self.assertEqual(
            self.admin.list_display,
            (
                "logo_thumbnail",
                "name",
                "location",
                "position",
                "active",
                "open_in_new_tab",
                "updated_at",
            ),
        )
        self.assertEqual(self.admin.list_editable, ("position", "active"))
        self.assertIn("active", self.admin.list_filter)
        self.assertIn("location", self.admin.list_filter)
        self.assertIn("name", self.admin.search_fields)
        self.assertIn("location__key", self.admin.search_fields)
        self.assertIn("activate_services", self.admin.actions)
        self.assertIn("deactivate_services", self.admin.actions)

    def _request(self):
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory

        request = RequestFactory().post("/")
        request.user = self.user
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))
        return request


class PersianAdminTranslationTests(SimpleTestCase):
    """Ensure admin-facing strings translate when language is Persian."""

    def test_persian_translations_for_admin_strings(self) -> None:
        from django.utils import translation
        from django.utils.translation import gettext as _
        from django.utils.translation import ngettext

        from ecosystem.apps import EcosystemConfig
        from ecosystem.models import Service

        with translation.override("fa"):
            self.assertEqual(str(EcosystemConfig.verbose_name), "اکوسیستم")
            self.assertEqual(str(Service._meta.verbose_name), "سرویس")
            self.assertEqual(str(Service._meta.verbose_name_plural), "سرویس‌ها")
            self.assertEqual(str(Service._meta.get_field("name").verbose_name), "نام")
            self.assertEqual(
                str(Service._meta.get_field("open_in_new_tab").verbose_name),
                "باز شدن در زبانه جدید",
            )
            self.assertEqual(
                str(Service._meta.get_field("active").help_text),
                "برای پنهان کردن این سرویس در همه جا بدون حذف آن، تیک را بردارید.",
            )
            self.assertEqual(_("Placement"), "محل نمایش")
            self.assertEqual(_("Logo preview"), "پیش‌نمایش لوگو")
            self.assertEqual(_("Link behavior"), "رفتار پیوند")
            self.assertEqual(_("Timestamps"), "زمان‌ها")
            self.assertEqual(
                _("Activate selected services"),
                "فعال‌سازی سرویس‌های انتخاب‌شده",
            )
            self.assertEqual(
                _("Deactivate selected services"),
                "غیرفعال‌سازی سرویس‌های انتخاب‌شده",
            )
            self.assertEqual(
                ngettext(
                    "%d service was activated.",
                    "%d services were activated.",
                    1,
                )
                % 1,
                "1 سرویس فعال شد.",
            )
            self.assertEqual(
                ngettext(
                    "%d service was activated.",
                    "%d services were activated.",
                    2,
                )
                % 2,
                "2 سرویس فعال شدند.",
            )

    def test_english_fallback_remains_available(self) -> None:
        from django.utils import translation
        from django.utils.translation import gettext as _

        with translation.override("en"):
            self.assertEqual(_("Ecosystem"), "Ecosystem")
            self.assertEqual(_("services"), "services")
            self.assertEqual(
                _("Activate selected services"),
                "Activate selected services",
            )
