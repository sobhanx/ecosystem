"""Admin forms for ecosystem services."""

from __future__ import annotations

from typing import Any

from django import forms
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .models import Service


class ServiceAdminForm(forms.ModelForm):
    """Model form tuned for non-technical editors in Django Admin."""

    class Meta:
        model = Service
        # Position is system-managed; shown read-only via ModelAdmin.
        exclude = ("position",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        location = self.fields["location"]
        location.label = _("Placement")
        location.help_text = _(
            "Choose the placement this service belongs to. Prefer managing "
            "services from Ecosystem → Locations. The location key must match "
            'the template tag argument (example key: "footer").'
        )

        self.fields["logo"].help_text = _(
            "Optional square or wide image. Prefer PNG or SVG-compatible "
            "raster logos with a transparent background."
        )
        self.fields["slug"].help_text = _(
            "Internal unique ID. Leave blank to generate from the name; "
            "change only if you know why you need a stable custom value."
        )

    def clean(self) -> dict[str, Any]:
        """Generate a slug before model validation when the field is blank."""
        cleaned = super().clean()
        slug = (cleaned.get("slug") or "").strip()
        if slug:
            cleaned["slug"] = slug
            return cleaned

        base = slugify(cleaned.get("name") or "") or "service"
        candidate = base
        suffix = 2
        queryset = Service.objects.all()
        if self.instance.pk is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        while queryset.filter(slug=candidate).exists():
            candidate = f"{base}-{suffix}"
            suffix += 1
        cleaned["slug"] = candidate
        return cleaned
