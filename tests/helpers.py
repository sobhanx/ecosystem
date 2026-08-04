"""Shared helpers for ecosystem tests."""

from __future__ import annotations

from django.test import TestCase

from ecosystem.models import Location, Service


def make_location(key: str, **kwargs) -> Location:
    """Create a location with sensible defaults for tests."""
    defaults = {
        "name": kwargs.pop("name", key.replace("_", " ").title()),
        "active": True,
    }
    defaults.update(kwargs)
    return Location.objects.create(key=key, **defaults)


def assert_dense_positions(testcase: TestCase, location: Location) -> list[Service]:
    """Assert services for ``location`` use positions ``0..n-1`` with no gaps."""
    services = list(
        Service.objects.filter(location=location).order_by("position", "pk")
    )
    positions = [service.position for service in services]
    testcase.assertEqual(
        positions,
        list(range(len(services))),
        f"Expected dense positions for {location.key!r}, got {positions}",
    )
    return services
