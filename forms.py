"""Admin forms and widgets for ecosystem services."""

from __future__ import annotations

from typing import Any

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .models import Service


def get_location_suggestions() -> list[tuple[str, str]]:
    """
    Build ``(key, label)`` suggestions for the location field.

    Sources (in order, de-duplicated by key):

    1. Optional host setting ``ECOSYSTEM_LOCATIONS`` — either
       ``("footer", "Footer")`` pairs or bare ``"footer"`` strings.
    2. Distinct ``location`` values already stored on ``Service`` rows.

    The app never ships host-specific keys. Hosts opt in via settings;
    previously used keys remain selectable automatically.
    """
    seen: set[str] = set()
    suggestions: list[tuple[str, str]] = []

    for item in getattr(settings, "ECOSYSTEM_LOCATIONS", ()) or ():
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            key, label = str(item[0]).strip(), str(item[1]).strip()
        else:
            key = str(item).strip()
            label = key
        if not key or key in seen:
            continue
        seen.add(key)
        suggestions.append((key, label or key))

    existing = (
        Service.objects.order_by("location")
        .values_list("location", flat=True)
        .distinct()
    )
    for key in existing:
        key = (key or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        suggestions.append((key, key))

    return suggestions


class LocationInput(forms.TextInput):
    """
    Text input with an HTML5 datalist of known placement keys.

    Editors can pick a suggestion or type a new key. No JavaScript required.
    """

    def __init__(self, suggestions: list[tuple[str, str]] | None = None, attrs=None):
        default_attrs = {
            "class": "vTextField",
            "autocomplete": "off",
            "spellcheck": "false",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
        self.suggestions = suggestions or []

    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        datalist_id = f"id_{name}_suggestions"
        context["widget"]["attrs"]["list"] = datalist_id
        context["datalist_id"] = datalist_id
        context["suggestions"] = self.suggestions
        return context

    template_name = "ecosystem/widgets/location_input.html"


class ServiceAdminForm(forms.ModelForm):
    """Model form tuned for non-technical editors in Django Admin."""

    class Meta:
        model = Service
        fields = "__all__"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        suggestions = get_location_suggestions()
        location = self.fields["location"]
        location.widget = LocationInput(suggestions=suggestions)
        location.help_text = _(
            "Choose where this service appears on the site. Pick a known "
            "placement from the suggestions, or type a new key that matches "
            "the location argument in the template tag "
            '(example key: "footer").'
        )
        location.label = _("Placement")

        self.fields["name"].help_text = _(
            'Short label visitors and editors will recognize '
            '(for example "Academy" or "Shop").'
        )
        self.fields["url"].help_text = _(
            "Full web address, including https:// "
            "(for example https://academy.example.com)."
        )
        self.fields["description"].help_text = _(
            "Optional notes for your team. Not shown on the site by default."
        )
        self.fields["logo"].help_text = _(
            "Optional square or wide image. Prefer PNG or SVG-compatible "
            "raster logos with a transparent background."
        )
        self.fields["slug"].help_text = _(
            "Internal unique ID. Leave blank to generate from the name; "
            "change only if you know why you need a stable custom value."
        )
        self.fields["display_order"].help_text = _(
            "Controls the order within the same placement. "
            "Smaller numbers appear first (0, 1, 2, …)."
        )
        self.fields["active"].help_text = _(
            "Uncheck to hide this service everywhere without deleting it."
        )
        self.fields["open_in_new_tab"].help_text = _(
            "When checked, the link opens in a new browser tab."
        )
