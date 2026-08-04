"""Read helpers for ecosystem locations and services.

Template tags and other callers should use these helpers for rendering lookups
so filtering and ordering stay consistent. This module must not mutate data.
"""

from __future__ import annotations

from collections.abc import Sequence

from django.db.models import QuerySet

from .models import Location, Service

# Canonical service order within a location (shared with write-layer ordering).
SERVICE_ORDER = ("position", "pk")


def get_location_by_key(key: str) -> Location | None:
    """
    Resolve an active ``Location`` by its template-tag key.

    Use this when callers need the Location object itself (Admin helpers, host
    code). Template rendering should prefer :func:`get_active_services`, which
    keeps a single JOIN query for the hot path.
    """
    normalized = key.strip()
    if not normalized:
        return None
    return (
        Location.objects.filter(key=normalized, active=True)
        .only("id", "key", "name", "active")
        .first()
    )


def get_services_for_location(location: Location) -> QuerySet[Service]:
    """Return all services for ``location``, ordered canonically."""
    return Service.objects.filter(location=location).order_by(*SERVICE_ORDER)


def get_service_for_location(
    location: Location,
    service_id: int | str,
) -> Service | None:
    """Return a service that belongs to ``location``, or ``None``."""
    try:
        return Service.objects.get(pk=service_id, location=location)
    except (Service.DoesNotExist, TypeError, ValueError):
        return None


def get_location_services_by_ids(
    location: Location,
    ids: Sequence[int],
) -> list[Service]:
    """
    Return services for ``location`` whose PKs are in ``ids``.

    Order matches the location's canonical service order. Callers that require
    an exact ID match should compare lengths themselves.
    """
    return list(
        Service.objects.filter(location=location, pk__in=ids).order_by(*SERVICE_ORDER)
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
        ).order_by(*SERVICE_ORDER)
    )
