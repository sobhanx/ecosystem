"""Application configuration for the ecosystem reusable app."""

from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EcosystemConfig(AppConfig):
    """Default configuration for the ecosystem application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ecosystem"
    label = "ecosystem"
    verbose_name = _("Ecosystem")
