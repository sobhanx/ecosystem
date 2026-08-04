"""Packaging smoke tests for release artifacts."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_SOURCE_PATHS = (
    "lookups.py",
    "admin/__init__.py",
    "admin/location.py",
    "admin/service.py",
    "admin/workspace.py",
    "admin/helpers.py",
    "migrations/0004_location_and_service_fk.py",
    "migrations/0005_alter_service_ordering.py",
    "migrations/0006_alter_field_help_texts.py",
    "templates/admin/ecosystem/location_workspace.html",
    "templates/ecosystem/services.html",
    "static/ecosystem/vendor/Sortable.min.js",
    "static/ecosystem/workspace_sortable.js",
    "static/ecosystem/admin_copy.js",
    "locale/fa/LC_MESSAGES/django.mo",
)

REQUIRED_PACKAGE_FRAGMENTS = (
    "ecosystem/__init__.py",
    "ecosystem/lookups.py",
    "ecosystem/services.py",
    "ecosystem/admin/__init__.py",
    "ecosystem/admin/location.py",
    "ecosystem/admin/service.py",
    "ecosystem/admin/workspace.py",
    "ecosystem/admin/helpers.py",
    "ecosystem/migrations/0004_location_and_service_fk.py",
    "ecosystem/migrations/0005_alter_service_ordering.py",
    "ecosystem/migrations/0006_alter_field_help_texts.py",
    "ecosystem/templates/admin/ecosystem/location_workspace.html",
    "ecosystem/templates/ecosystem/services.html",
    "ecosystem/static/ecosystem/vendor/Sortable.min.js",
    "ecosystem/static/ecosystem/workspace_sortable.js",
    "ecosystem/static/ecosystem/admin_copy.js",
    "ecosystem/locale/fa/LC_MESSAGES/django.mo",
)

# Flat package layout: sdist stores package files at the project root.
REQUIRED_SDIST_FRAGMENTS = (
    "__init__.py",
    "lookups.py",
    "services.py",
    "admin/__init__.py",
    "admin/location.py",
    "admin/service.py",
    "admin/workspace.py",
    "admin/helpers.py",
    "migrations/0004_location_and_service_fk.py",
    "migrations/0005_alter_service_ordering.py",
    "migrations/0006_alter_field_help_texts.py",
    "templates/admin/ecosystem/location_workspace.html",
    "templates/ecosystem/services.html",
    "static/ecosystem/vendor/Sortable.min.js",
    "static/ecosystem/workspace_sortable.js",
    "static/ecosystem/admin_copy.js",
    "locale/fa/LC_MESSAGES/django.mo",
)


def _assert_fragments(
    testcase: SimpleTestCase,
    names: set[str],
    fragments: tuple[str, ...],
    label: str,
) -> None:
    for fragment in fragments:
        testcase.assertIn(fragment, names, f"missing {fragment} in {label}")


class PackagingSmokeTests(SimpleTestCase):
    """Assert source packaging inputs and built wheel/sdist contents."""

    def test_source_tree_contains_packaged_assets(self) -> None:
        for relative in REQUIRED_SOURCE_PATHS:
            path = REPO_ROOT / relative
            self.assertTrue(path.is_file(), f"missing source asset: {relative}")

    def test_package_modules_are_importable_from_source_tree(self) -> None:
        self.assertIsNotNone(importlib.util.find_spec("ecosystem"))
        self.assertIsNotNone(importlib.util.find_spec("ecosystem.lookups"))
        self.assertIsNotNone(importlib.util.find_spec("ecosystem.migrations"))
        import ecosystem

        self.assertEqual(ecosystem.__version__, "2.2.0")

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
            self.assertIn("2.2.0", wheel_path.name)

            with zipfile.ZipFile(wheel_path) as archive:
                names = set(archive.namelist())
                _assert_fragments(
                    self, names, REQUIRED_PACKAGE_FRAGMENTS, wheel_path.name
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
            self.assertTrue((installed / "admin" / "workspace.py").is_file())

            check = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import django\n"
                        "from django.conf import settings\n"
                        "settings.configure(\n"
                        "    INSTALLED_APPS=["
                        "'django.contrib.contenttypes',"
                        "'django.contrib.auth',"
                        "'ecosystem'"
                        "],\n"
                        "    DATABASES={'default': {"
                        "'ENGINE': 'django.db.backends.sqlite3',"
                        "'NAME': ':memory:'"
                        "}},\n"
                        "    SECRET_KEY='packaging-check',\n"
                        "    USE_TZ=True,\n"
                        ")\n"
                        "django.setup()\n"
                        "from django.core.management import call_command\n"
                        "call_command('check')\n"
                        "import ecosystem\n"
                        "assert ecosystem.__version__ == '2.2.0'\n"
                    ),
                ],
                capture_output=True,
                text=True,
                check=False,
                env={
                    **os.environ,
                    "PYTHONPATH": (
                        str(install_root)
                        + os.pathsep
                        + os.environ.get("PYTHONPATH", "")
                    ),
                },
            )
            self.assertEqual(
                check.returncode,
                0,
                f"installed package check failed:\n{check.stdout}\n{check.stderr}",
            )

    def test_sdist_contains_required_runtime_assets(self) -> None:
        try:
            from setuptools.build_meta import build_sdist
        except ImportError:
            self.skipTest("setuptools.build_meta is unavailable")

        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            previous_cwd = Path.cwd()
            try:
                os.chdir(REPO_ROOT)
                sdist_name = build_sdist(str(outdir))
            finally:
                os.chdir(previous_cwd)

            sdist_path = outdir / sdist_name
            self.assertTrue(sdist_path.is_file(), f"missing sdist {sdist_path}")
            self.assertIn("2.2.0", sdist_path.name)

            with tarfile.open(sdist_path, "r:gz") as archive:
                names = set(archive.getnames())
            # Sdist nests files under a top-level project directory.
            flattened = {
                "/".join(Path(name).parts[1:]) if Path(name).parts else name
                for name in names
            }
            _assert_fragments(
                self, flattened, REQUIRED_SDIST_FRAGMENTS, sdist_path.name
            )
