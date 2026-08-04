"""Read helpers for ecosystem locations and services.

Template tags and other callers should use these helpers for rendering lookups
so filtering and ordering stay consistent.
"""

from __future__ import annotations

from django.db.models import QuerySet

from .models import Location, Service


def get_location_by_key(key: str) -> Location | None:
    """Return the active location for ``key``, or ``None`` if missing/inactive."""
    normalized = key.strip()
    if not normalized:
        return None
    return (
        Location.objects.filter(key=normalized, active=True)
        .only("id", "key", "name", "active")
        .first()
    )


def get_active_services(location: str) -> QuerySet[Service]:
    """
    Return active services for the location ``key``, ordered by position then pk.

    Matching is against ``Location.key`` after stripping surrounding whitespace.
    Missing keys and inactive locations yield an empty queryset.

    Args:
        location: Placement key (for example ``"footer"`` or ``"pricing_page"``).

    Returns:
        An unevaluated queryset of matching ``Service`` rows.
    """
    normalized = location.strip()
    if not normalized:
        return Service.objects.none()
    return (
        Service.objects.filter(
            active=True,
            location__key=normalized,
            location__active=True,
        ).order_by("position", "pk")
    )
