"""Query helpers for ecosystem services.

All rendering lookups must go through this module so active/location filtering
and ordering stay in one place. Template tags, views, and management commands
should call these helpers instead of querying ``Service`` directly.
"""

from __future__ import annotations

from django.db.models import QuerySet

from .models import Service


def get_active_services(location: str) -> QuerySet[Service]:
    """
    Return active services for ``location``, ordered by display order then name.

    Matching is exact against ``Service.location`` after stripping surrounding
    whitespace from the requested key (admin values are also stripped on save).

    Args:
        location: Free-form placement key (for example ``"footer"`` or
            ``"pricing_page"``).

    Returns:
        An unevaluated queryset of matching ``Service`` rows.
    """
    return (
        Service.objects.filter(active=True, location=location.strip())
        .order_by("display_order", "name")
    )
