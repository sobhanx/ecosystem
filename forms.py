"""Admin forms for ecosystem services."""

from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Service


class ServiceAdminForm(forms.ModelForm):
    """Model form tuned for non-technical editors in Django Admin."""

    class Meta:
        model = Service
        fields = "__all__"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        location = self.fields["location"]
        location.label = _("Placement")
        location.help_text = _(
            "Choose the placement this service belongs to. Create locations "
            "under Ecosystem → Locations. The location key must match the "
            "template tag argument (example key: \"footer\")."
        )

        # Admin-only help text; other fields inherit ``help_text`` from the model.
        self.fields["logo"].help_text = _(
            "Optional square or wide image. Prefer PNG or SVG-compatible "
            "raster logos with a transparent background."
        )
        self.fields["slug"].help_text = _(
            "Internal unique ID. Leave blank to generate from the name; "
            "change only if you know why you need a stable custom value."
        )
