"""Application configuration for the demo app."""

from __future__ import annotations

from django.apps import AppConfig


class DemoappConfig(AppConfig):
    """Local demo pages for previewing ecosystem rendering."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "demoapp"
    verbose_name = "Demo"
