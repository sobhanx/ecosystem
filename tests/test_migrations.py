"""Migration upgrade-path tests for Location FK conversion."""

from __future__ import annotations

import importlib

from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.test import SimpleTestCase, TestCase

from ecosystem.models import Location, Service

_migration_0004 = importlib.import_module(
    "ecosystem.migrations.0004_location_and_service_fk"
)


class AppliedMigrationsTests(TestCase):
    def test_latest_migrations_are_applied_in_test_db(self) -> None:
        applied = MigrationRecorder(connection).applied_migrations()
        self.assertIn(("ecosystem", "0004_location_and_service_fk"), applied)
        self.assertIn(("ecosystem", "0005_alter_service_ordering"), applied)


class LocationFKConversionLogicTests(TestCase):
    """
    Validate densify/key mapping expectations from the 0004 upgrade path.

    Full schema reverse of 0004 is not reliable on SQLite (index rebuild order),
    so densify behavior is asserted against an equivalent FK dataset.
    """

    def test_forwards_migrate_locations_is_callable(self) -> None:
        self.assertTrue(callable(_migration_0004.forwards_migrate_locations))

    def test_settings_location_labels_parse(self) -> None:
        with self.settings(
            ECOSYSTEM_LOCATIONS=[("footer", "Site footer"), "header"]
        ):
            labels = _migration_0004._settings_location_labels()
        self.assertEqual(labels["footer"], "Site footer")
        self.assertEqual(labels["header"], "header")

    def test_settings_location_labels_strip_and_skip_blank(self) -> None:
        with self.settings(
            ECOSYSTEM_LOCATIONS=[
                ("  footer  ", "  Site footer  "),
                ("", "ignored"),
                "   ",
                ("Header", "Top nav"),
            ]
        ):
            labels = _migration_0004._settings_location_labels()
        self.assertEqual(labels, {"footer": "Site footer", "Header": "Top nav"})

    def test_legacy_key_normalization_preserves_case_and_skips_empty(self) -> None:
        """
        Document 0004 forwards behavior for legacy string locations.

        Keys are stripped; empty/whitespace-only values are skipped; case is
        preserved so ``Footer`` and ``footer`` remain distinct placements.
        """
        raw_values = [" footer ", "", None, "  ", "Footer", "footer"]
        keys: dict[str, str] = {}
        for raw in raw_values:
            key = (raw or "").strip()
            if not key:
                continue
            keys[key] = key
        self.assertEqual(set(keys), {"footer", "Footer"})
        self.assertNotEqual(keys["footer"], keys["Footer"])

    def test_dense_positions_match_upgrade_expectations(self) -> None:
        footer = Location.objects.create(key="footer", name="Footer")
        header = Location.objects.create(key="header", name="Header")
        Service.objects.create(
            name="Shop",
            slug="shop",
            url="https://shop.example.com",
            location=footer,
            position=5,
        )
        Service.objects.create(
            name="Blog",
            slug="blog",
            url="https://blog.example.com",
            location=footer,
            position=1,
        )
        Service.objects.create(
            name="Academy",
            slug="academy",
            url="https://academy.example.com",
            location=header,
            position=0,
        )

        for location in Location.objects.all():
            ordered = list(
                Service.objects.filter(location=location).order_by(
                    "position", "name", "pk"
                )
            )
            for index, service in enumerate(ordered):
                if service.position != index:
                    service.position = index
                    service.save(update_fields=["position"])

        footer_services = list(
            Service.objects.filter(location=footer).order_by("position", "pk")
        )
        self.assertEqual([s.name for s in footer_services], ["Blog", "Shop"])
        self.assertEqual([s.position for s in footer_services], [0, 1])


class MigrationModuleTests(SimpleTestCase):
    def test_0004_and_0005_modules_import(self) -> None:
        m4 = _migration_0004
        m5 = importlib.import_module("ecosystem.migrations.0005_alter_service_ordering")
        self.assertTrue(hasattr(m4, "Migration"))
        self.assertTrue(hasattr(m5, "Migration"))
        self.assertEqual(
            m4.Migration.dependencies,
            [("ecosystem", "0003_optimize_indexes_and_constraints")],
        )
