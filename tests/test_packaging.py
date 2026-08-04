"""Packaging smoke tests for release artifacts."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_SOURCE_PATHS = (
    "lookups.py",
    "migrations/0004_location_and_service_fk.py",
    "migrations/0005_alter_service_ordering.py",
    "templates/admin/ecosystem/location_workspace.html",
    "templates/ecosystem/services.html",
    "static/ecosystem/vendor/Sortable.min.js",
    "static/ecosystem/workspace_sortable.js",
    "static/ecosystem/admin_copy.js",
    "locale/fa/LC_MESSAGES/django.mo",
)

REQUIRED_WHEEL_FRAGMENTS = (
    "ecosystem/__init__.py",
    "ecosystem/lookups.py",
    "ecosystem/services.py",
    "ecosystem/admin.py",
    "ecosystem/migrations/0004_location_and_service_fk.py",
    "ecosystem/migrations/0005_alter_service_ordering.py",
    "ecosystem/templates/admin/ecosystem/location_workspace.html",
    "ecosystem/templates/ecosystem/services.html",
    "ecosystem/static/ecosystem/vendor/Sortable.min.js",
    "ecosystem/static/ecosystem/workspace_sortable.js",
    "ecosystem/static/ecosystem/admin_copy.js",
    "ecosystem/locale/fa/LC_MESSAGES/django.mo",
)


class PackagingSmokeTests(SimpleTestCase):
    """Assert source packaging inputs and built wheel contents."""

    def test_source_tree_contains_packaged_assets(self) -> None:
        for relative in REQUIRED_SOURCE_PATHS:
            path = REPO_ROOT / relative
            self.assertTrue(path.is_file(), f"missing source asset: {relative}")

    def test_package_modules_are_importable_from_source_tree(self) -> None:
        self.assertIsNotNone(importlib.util.find_spec("ecosystem"))
        self.assertIsNotNone(importlib.util.find_spec("ecosystem.lookups"))
        self.assertIsNotNone(importlib.util.find_spec("ecosystem.migrations"))
        import ecosystem

        self.assertEqual(ecosystem.__version__, "2.1.0")

    def test_wheel_contains_required_runtime_assets(self) -> None:
        try:
            from setuptools.build_meta import build_wheel
        except ImportError:
            self.skipTest("setuptools.build_meta is unavailable")

        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            previous_cwd = Path.cwd()
            try:
                os.chdir(REPO_ROOT)
                wheel_name = build_wheel(str(outdir))
            finally:
                os.chdir(previous_cwd)

            wheel_path = outdir / wheel_name
            self.assertTrue(wheel_path.is_file(), f"missing wheel {wheel_path}")
            self.assertIn("2.1.0", wheel_path.name)

            with zipfile.ZipFile(wheel_path) as archive:
                names = set(archive.namelist())
                for fragment in REQUIRED_WHEEL_FRAGMENTS:
                    self.assertIn(
                        fragment,
                        names,
                        f"missing {fragment} in {wheel_path.name}",
                    )

            install_root = outdir / "install"
            install_root.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--target",
                    str(install_root),
                    str(wheel_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"pip install failed:\n{result.stdout}\n{result.stderr}",
            )
            installed = install_root / "ecosystem"
            self.assertTrue((installed / "lookups.py").is_file())
            self.assertTrue(
                (
                    installed
                    / "static"
                    / "ecosystem"
                    / "vendor"
                    / "Sortable.min.js"
                ).is_file()
            )
            self.assertTrue(
                (
                    installed
                    / "templates"
                    / "admin"
                    / "ecosystem"
                    / "location_workspace.html"
                ).is_file()
            )
            self.assertTrue(
                (installed / "migrations" / "0004_location_and_service_fk.py").is_file()
            )
