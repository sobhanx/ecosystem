"""Tests for ecosystem write service operations."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from ecosystem.models import Location, Service
from ecosystem.services import (
    delete_service,
    duplicate_service,
    move_service_down,
    move_service_to_bottom,
    move_service_to_top,
    move_service_up,
    move_services,
    quick_add_service,
    reorder_services,
    set_services_active,
)


def make_location(key: str, **kwargs) -> Location:
    defaults = {
        "name": kwargs.pop("name", key.replace("_", " ").title()),
        "active": True,
    }
    defaults.update(kwargs)
    return Location.objects.create(key=key, **defaults)


def names(location: Location) -> list[str]:
    return list(
        Service.objects.filter(location=location)
        .order_by("position", "pk")
        .values_list("name", flat=True)
    )


def positions(location: Location) -> list[int]:
    return list(
        Service.objects.filter(location=location)
        .order_by("position", "pk")
        .values_list("position", flat=True)
    )


class QuickAddServiceTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer")

    def test_quick_add_appends_with_defaults(self) -> None:
        academy = quick_add_service(
            self.footer, "Academy", "https://academy.example.com"
        )
        shop = quick_add_service(self.footer, "Shop", "https://shop.example.com")
        blog = quick_add_service(self.footer, "Blog", "https://blog.example.com")

        self.assertEqual(academy.position, 0)
        self.assertEqual(shop.position, 1)
        self.assertEqual(blog.position, 2)
        self.assertTrue(blog.active)
        self.assertTrue(blog.open_in_new_tab)
        self.assertEqual(names(self.footer), ["Academy", "Shop", "Blog"])
        self.assertEqual(positions(self.footer), [0, 1, 2])

    def test_quick_add_rejects_explicit_position(self) -> None:
        with self.assertRaises(ValidationError):
            quick_add_service(
                self.footer,
                "Shop",
                "https://shop.example.com",
                position=99,
            )


class ReorderServicesTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer")
        self.header = make_location("header")
        self.academy = quick_add_service(
            self.footer, "Academy", "https://academy.example.com"
        )
        self.shop = quick_add_service(self.footer, "Shop", "https://shop.example.com")
        self.blog = quick_add_service(self.footer, "Blog", "https://blog.example.com")
        self.header_only = quick_add_service(
            self.header, "Search", "https://search.example.com"
        )

    def test_reorder_persists_dense_positions(self) -> None:
        reorder_services(
            self.footer,
            [self.blog.pk, self.academy.pk, self.shop.pk],
        )
        self.assertEqual(names(self.footer), ["Blog", "Academy", "Shop"])
        self.assertEqual(positions(self.footer), [0, 1, 2])

    def test_reorder_rejects_ids_from_other_location(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            reorder_services(
                self.footer,
                [self.blog.pk, self.academy.pk, self.header_only.pk],
            )
        self.assertIn("not in this location", str(ctx.exception))

    def test_reorder_rejects_incomplete_list(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            reorder_services(self.footer, [self.blog.pk, self.academy.pk])
        self.assertIn("exactly the services", str(ctx.exception))

    def test_reorder_rejects_duplicates(self) -> None:
        with self.assertRaises(ValidationError):
            reorder_services(
                self.footer,
                [self.blog.pk, self.blog.pk, self.academy.pk],
            )


class MoveServicesTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer")
        self.header = make_location("header")
        self.academy = quick_add_service(
            self.footer, "Academy", "https://academy.example.com"
        )
        self.blog = quick_add_service(self.footer, "Blog", "https://blog.example.com")
        self.search = quick_add_service(
            self.header, "Search", "https://search.example.com"
        )

    def test_move_appends_and_renumbers_source(self) -> None:
        move_services([self.blog], self.header)

        self.assertEqual(names(self.footer), ["Academy"])
        self.assertEqual(positions(self.footer), [0])
        self.assertEqual(names(self.header), ["Search", "Blog"])
        self.assertEqual(positions(self.header), [0, 1])

        self.blog.refresh_from_db()
        self.assertEqual(self.blog.location_id, self.header.pk)
        self.assertEqual(self.blog.position, 1)

    def test_move_queryset_preserves_input_order_when_appending(self) -> None:
        docs = quick_add_service(self.footer, "Docs", "https://docs.example.com")
        move_services([self.academy, docs], self.header)
        self.assertEqual(names(self.footer), ["Blog"])
        self.assertEqual(names(self.header), ["Search", "Academy", "Docs"])


class DuplicateServiceTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer")

    def test_duplicate_creates_independent_object_at_end(self) -> None:
        shop = quick_add_service(self.footer, "Shop", "https://shop.example.com")
        quick_add_service(self.footer, "Blog", "https://blog.example.com")

        copy = duplicate_service(shop)

        self.assertNotEqual(copy.pk, shop.pk)
        self.assertEqual(copy.name, "Shop")
        self.assertEqual(copy.url, shop.url)
        self.assertEqual(copy.location_id, self.footer.pk)
        self.assertEqual(copy.position, 2)
        self.assertEqual(names(self.footer), ["Shop", "Blog", "Shop"])

    def test_duplicate_handles_slug_conflicts(self) -> None:
        shop = quick_add_service(
            self.footer,
            "Shop",
            "https://shop.example.com",
            slug="shop",
        )
        copy = duplicate_service(shop)
        self.assertEqual(shop.slug, "shop")
        self.assertEqual(copy.slug, "shop-2")
        self.assertNotEqual(copy.slug, shop.slug)

    def test_duplicate_keeps_logo_reference(self) -> None:
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        original = quick_add_service(
            self.footer,
            "Shop",
            "https://shop.example.com",
            logo=SimpleUploadedFile("logo.png", png, content_type="image/png"),
        )
        copy = duplicate_service(original)
        self.assertTrue(copy.logo)
        self.assertEqual(copy.logo.name, original.logo.name)


class SetServicesActiveTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer")
        self.academy = quick_add_service(
            self.footer, "Academy", "https://academy.example.com"
        )
        self.shop = quick_add_service(self.footer, "Shop", "https://shop.example.com")

    def test_bulk_deactivate_queryset(self) -> None:
        updated = set_services_active(
            Service.objects.filter(location=self.footer),
            False,
        )
        self.assertEqual(updated, 2)
        self.academy.refresh_from_db()
        self.shop.refresh_from_db()
        self.assertFalse(self.academy.active)
        self.assertFalse(self.shop.active)

    def test_bulk_activate_iterable(self) -> None:
        set_services_active([self.academy, self.shop], False)
        updated = set_services_active([self.academy], True)
        self.assertEqual(updated, 1)
        self.academy.refresh_from_db()
        self.shop.refresh_from_db()
        self.assertTrue(self.academy.active)
        self.assertFalse(self.shop.active)

    def test_delete_service_renumbers(self) -> None:
        delete_service(self.academy)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.position, 0)
        self.assertEqual(Service.objects.filter(location=self.footer).count(), 1)
        self.assertEqual(positions(self.footer), [0])


class NudgeServiceTests(TestCase):
    def setUp(self) -> None:
        self.footer = make_location("footer")
        self.academy = quick_add_service(
            self.footer, "Academy", "https://academy.example.com"
        )
        self.shop = quick_add_service(self.footer, "Shop", "https://shop.example.com")
        self.blog = quick_add_service(self.footer, "Blog", "https://blog.example.com")

    def test_move_up_and_down(self) -> None:
        move_service_up(self.shop)
        self.assertEqual(names(self.footer), ["Shop", "Academy", "Blog"])
        self.assertEqual(positions(self.footer), [0, 1, 2])

        move_service_down(self.shop)
        self.assertEqual(names(self.footer), ["Academy", "Shop", "Blog"])

    def test_move_up_at_top_is_noop(self) -> None:
        move_service_up(self.academy)
        self.assertEqual(names(self.footer), ["Academy", "Shop", "Blog"])

    def test_move_down_at_bottom_is_noop(self) -> None:
        move_service_down(self.blog)
        self.assertEqual(names(self.footer), ["Academy", "Shop", "Blog"])

    def test_move_to_top_and_bottom(self) -> None:
        move_service_to_top(self.blog)
        self.assertEqual(names(self.footer), ["Blog", "Academy", "Shop"])
        self.assertEqual(positions(self.footer), [0, 1, 2])

        move_service_to_bottom(self.blog)
        self.assertEqual(names(self.footer), ["Academy", "Shop", "Blog"])
        self.assertEqual(positions(self.footer), [0, 1, 2])

    def test_nudge_missing_service_raises_validation_error(self) -> None:
        deleted = self.shop
        delete_service(deleted)
        with self.assertRaises(ValidationError) as ctx:
            move_service_up(deleted)
        self.assertIn("no longer available", str(ctx.exception))
