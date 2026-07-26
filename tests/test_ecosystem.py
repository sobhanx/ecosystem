"""Tests for the ecosystem reusable application."""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.template import Context, Template
from django.test import SimpleTestCase, TestCase, override_settings

from ecosystem.models import Service
from ecosystem.services import get_active_services


class ServiceModelTests(TestCase):
    """Unit tests for the ``Service`` model."""

    def test_str_returns_name(self) -> None:
        service = Service(name="Academy", url="https://academy.example.com")
        self.assertEqual(str(service), "Academy")

    def test_default_field_values(self) -> None:
        service = Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location="footer",
        )
        self.assertEqual(service.display_order, 0)
        self.assertTrue(service.active)
        self.assertTrue(service.open_in_new_tab)
        self.assertEqual(service.location, "footer")
        self.assertEqual(service.slug, "shop")
        self.assertEqual(service.description, "")

    def test_slug_is_generated_from_name_when_empty(self) -> None:
        service = Service.objects.create(
            name="My Academy",
            url="https://academy.example.com",
            location="header",
        )
        self.assertEqual(service.slug, "my-academy")

    def test_slug_is_not_regenerated_when_already_set(self) -> None:
        service = Service.objects.create(
            name="Academy",
            slug="custom-academy",
            url="https://academy.example.com",
            location="header",
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
            location="header",
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
            location="footer",
        )
        duplicate = Service.objects.create(
            name="Shop",
            url="https://shop-b.example.com",
            location="footer",
        )
        self.assertEqual(duplicate.slug, "shop-2")

    def test_slug_must_be_unique(self) -> None:
        Service.objects.create(
            name="Shop",
            slug="shop",
            url="https://shop.example.com",
            location="footer",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Service.objects.create(
                    name="Other Shop",
                    slug="shop",
                    url="https://other.example.com",
                    location="footer",
                )

    def test_location_is_stripped_on_save(self) -> None:
        service = Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location="  footer  ",
        )
        self.assertEqual(service.location, "footer")

    def test_description_is_optional(self) -> None:
        service = Service.objects.create(
            name="Blog",
            url="https://blog.example.com",
            location="article_bottom",
            description="Sibling blog for long-form content.",
        )
        self.assertEqual(
            service.description,
            "Sibling blog for long-form content.",
        )

    def test_meta_ordering_by_display_order_then_name(self) -> None:
        Service.objects.create(
            name="Zebra",
            url="https://zebra.example.com",
            location="header",
            display_order=2,
        )
        Service.objects.create(
            name="Alpha",
            url="https://alpha.example.com",
            location="header",
            display_order=1,
        )
        Service.objects.create(
            name="Beta",
            url="https://beta.example.com",
            location="header",
            display_order=1,
        )

        names = list(Service.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Alpha", "Beta", "Zebra"])

    def test_location_accepts_arbitrary_strings(self) -> None:
        service = Service.objects.create(
            name="Pricing CTA",
            url="https://shop.example.com/pricing",
            location="pricing_page",
        )
        self.assertEqual(service.location, "pricing_page")


class ActiveServicesQueryTests(TestCase):
    """Tests for ``get_active_services`` filtering and ordering."""

    def setUp(self) -> None:
        self.footer_first = Service.objects.create(
            name="Blog",
            url="https://blog.example.com",
            location="footer",
            display_order=1,
            active=True,
        )
        self.footer_second = Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location="footer",
            display_order=2,
            active=True,
        )
        self.footer_inactive = Service.objects.create(
            name="Legacy",
            url="https://legacy.example.com",
            location="footer",
            display_order=0,
            active=False,
        )
        self.header_service = Service.objects.create(
            name="Academy",
            url="https://academy.example.com",
            location="header",
            display_order=0,
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
        custom = Service.objects.create(
            name="Dashboard Widget",
            url="https://dashboard.example.com",
            location="dashboard_left",
            active=True,
        )
        services = list(get_active_services("dashboard_left"))
        self.assertEqual(services, [custom])
        self.assertEqual(list(get_active_services("missing_key")), [])

    def test_query_layer_strips_location_argument(self) -> None:
        service = Service.objects.create(
            name="Docs Portal",
            url="https://docs.example.com",
            location="docs_nav",
            active=True,
        )
        self.assertEqual(list(get_active_services("  docs_nav  ")), [service])

    def test_ordering_by_display_order_then_name(self) -> None:
        Service.objects.create(
            name="Docs",
            url="https://docs.example.com",
            location="footer",
            display_order=1,
            active=True,
        )
        names = list(
            get_active_services("footer").values_list("name", flat=True)
        )
        self.assertEqual(names, ["Blog", "Docs", "Shop"])


class EcosystemTemplateTagTests(TestCase):
    """Tests for the ``ecosystem`` inclusion tag and legacy alias."""

    def setUp(self) -> None:
        self.active_footer = Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location="footer",
            display_order=1,
            active=True,
            open_in_new_tab=True,
        )
        Service.objects.create(
            name="Inactive Footer",
            url="https://inactive.example.com",
            location="footer",
            display_order=0,
            active=False,
        )
        Service.objects.create(
            name="Header Only",
            url="https://header.example.com",
            location="header",
            display_order=0,
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
        Service.objects.create(
            name="Same Tab",
            url="https://same.example.com",
            location="sidebar",
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
        Service.objects.create(
            name="Pricing",
            url="https://shop.example.com/pricing",
            location="pricing_page",
            active=True,
        )
        rendered = Template(
            "{% load ecosystem %}{% ecosystem 'pricing_page' %}"
        ).render(Context())
        self.assertIn("Pricing", rendered)


@override_settings(ROOT_URLCONF="ecosystem.urls")
class EcosystemUrlsTests(SimpleTestCase):
    """Ensure the app exposes a valid, empty URLConf in v1."""

    def test_urlpatterns_is_empty(self) -> None:
        from ecosystem.urls import app_name, urlpatterns

        self.assertEqual(app_name, "ecosystem")
        self.assertEqual(urlpatterns, [])


class LocationSuggestionsTests(TestCase):
    """Tests for admin location suggestion helpers."""

    def test_suggestions_include_existing_database_locations(self) -> None:
        from ecosystem.forms import get_location_suggestions

        Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location="footer",
        )
        Service.objects.create(
            name="Docs",
            url="https://docs.example.com",
            location="docs_nav",
        )

        suggestions = get_location_suggestions()
        keys = [key for key, _label in suggestions]
        self.assertEqual(keys, ["docs_nav", "footer"])

    @override_settings(
        ECOSYSTEM_LOCATIONS=[
            ("footer", "Site footer"),
            "header",
            ("footer", "Duplicate ignored"),
            "",
        ]
    )
    def test_suggestions_merge_settings_then_database(self) -> None:
        from ecosystem.forms import get_location_suggestions

        Service.objects.create(
            name="Pricing",
            url="https://shop.example.com/pricing",
            location="pricing_page",
        )
        Service.objects.create(
            name="Footer Shop",
            url="https://shop.example.com",
            location="footer",
        )

        suggestions = get_location_suggestions()
        self.assertEqual(
            suggestions,
            [
                ("footer", "Site footer"),
                ("header", "header"),
                ("pricing_page", "pricing_page"),
            ],
        )

    @override_settings(ECOSYSTEM_LOCATIONS=())
    def test_admin_form_uses_datalist_location_widget(self) -> None:
        from ecosystem.forms import LocationInput, ServiceAdminForm

        Service.objects.create(
            name="Shop",
            url="https://shop.example.com",
            location="footer",
        )
        form = ServiceAdminForm()
        widget = form.fields["location"].widget
        self.assertIsInstance(widget, LocationInput)
        self.assertEqual(widget.suggestions, [("footer", "footer")])
        rendered = widget.render("location", "footer")
        self.assertIn('list="id_location_suggestions"', rendered)
        self.assertIn('<datalist id="id_location_suggestions">', rendered)
        self.assertIn('value="footer"', rendered)


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

    def test_activate_and_deactivate_actions(self) -> None:
        active = Service.objects.create(
            name="Active",
            url="https://active.example.com",
            location="footer",
            active=True,
        )
        inactive = Service.objects.create(
            name="Inactive",
            url="https://inactive.example.com",
            location="footer",
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
            location="footer",
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
            location="footer",
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
                "display_order",
                "active",
                "open_in_new_tab",
                "updated_at",
            ),
        )
        self.assertEqual(self.admin.list_editable, ("display_order", "active"))
        self.assertIn("active", self.admin.list_filter)
        self.assertIn("location", self.admin.list_filter)
        self.assertIn("name", self.admin.search_fields)
        self.assertIn("location", self.admin.search_fields)
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
                str(Service._meta.get_field("display_order").verbose_name),
                "ترتیب نمایش",
            )
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
