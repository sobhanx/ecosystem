"""Write operations and compatibility exports for ecosystem services.

Read lookups live in ``ecosystem.lookups``. This module owns mutations used by
Admin (and tests) so ordering rules stay consistent in one place.

``get_active_services`` is re-exported for backward compatibility.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from .models import Location, Service
from .lookups import get_active_services

__all__ = [
    "get_active_services",
    "quick_add_service",
    "reorder_services",
    "move_services",
    "duplicate_service",
    "duplicate_services",
    "set_services_active",
    "delete_service",
    "move_service_up",
    "move_service_down",
    "move_service_to_top",
    "move_service_to_bottom",
]

# Canonical service order within a location.
SERVICE_ORDER = ("position", "pk")


def _services_for_location(location: Location) -> QuerySet[Service]:
    return Service.objects.filter(location=location).order_by(*SERVICE_ORDER)


def _lock_location(location: Location) -> Location:
    """Lock the location row for the duration of the surrounding transaction."""
    return Location.objects.select_for_update().get(pk=location.pk)


def _lock_location_services(location: Location) -> list[Service]:
    """Lock all services in ``location``, ordered canonically."""
    return list(
        Service.objects.select_for_update()
        .filter(location=location)
        .order_by(*SERVICE_ORDER)
    )


def _next_position_locked(location: Location) -> int:
    """
    Return the next append position while holding locks.

    Callers must already hold ``select_for_update`` on the location (and ideally
    its services) inside an atomic block.
    """
    return (
        Service.objects.filter(location=location)
        .order_by(*SERVICE_ORDER)
        .count()
    )


def _renumber_services(services: list[Service]) -> None:
    """Rewrite dense ``position`` values ``0..n-1`` for the given locked list."""
    updates: list[Service] = []
    now = timezone.now()
    for index, service in enumerate(services):
        if service.position != index:
            service.position = index
            service.updated_at = now
            updates.append(service)
    if updates:
        Service.objects.bulk_update(updates, ["position", "updated_at"])


def _renumber_location(location: Location) -> None:
    """Rewrite dense ``position`` values ``0..n-1`` for ``location``."""
    _renumber_services(list(_services_for_location(location)))


def _resolve_services(services: Iterable[Service] | QuerySet[Service]) -> list[Service]:
    if isinstance(services, QuerySet):
        return list(services.order_by("pk"))
    return list(services)


@transaction.atomic
def quick_add_service(
    location: Location,
    name: str,
    url: str,
    *,
    active: bool = True,
    open_in_new_tab: bool = True,
    description: str = "",
    **defaults,
) -> Service:
    """
    Create a service at the end of ``location``'s ordered list.

    Position is assigned automatically. Callers must not pass ``position``.
    """
    if "position" in defaults:
        raise ValidationError("position is assigned automatically; do not pass it.")
    if "location" in defaults:
        raise ValidationError("location is already provided as the first argument.")

    locked_location = _lock_location(location)
    _lock_location_services(locked_location)
    return Service.objects.create(
        location=locked_location,
        name=name,
        url=url,
        position=_next_position_locked(locked_location),
        active=active,
        open_in_new_tab=open_in_new_tab,
        description=description,
        **defaults,
    )


@transaction.atomic
def reorder_services(location: Location, ordered_ids: Sequence[int]) -> list[Service]:
    """
    Rewrite service order for ``location`` to match ``ordered_ids``.

    ``ordered_ids`` must contain each service of ``location`` exactly once.
    Services belonging to other locations are rejected. The operation is atomic
    and produces dense positions ``0..n-1``.
    """
    ids = [int(pk) for pk in ordered_ids]
    if len(ids) != len(set(ids)):
        raise ValidationError("ordered_ids must not contain duplicate service IDs.")

    _lock_location(location)
    locked = _lock_location_services(location)
    existing_ids = {service.pk for service in locked}
    requested_ids = set(ids)

    if requested_ids != existing_ids:
        missing = sorted(existing_ids - requested_ids)
        extra = sorted(requested_ids - existing_ids)
        details: list[str] = []
        if missing:
            details.append(f"missing IDs for this location: {missing}")
        if extra:
            details.append(f"IDs not in this location: {extra}")
        raise ValidationError(
            "ordered_ids must list exactly the services for this location "
            f"({'; '.join(details)})."
        )

    by_id = {service.pk: service for service in locked}
    updates: list[Service] = []
    ordered: list[Service] = []
    now = timezone.now()
    for index, pk in enumerate(ids):
        service = by_id[pk]
        if service.position != index:
            service.position = index
            service.updated_at = now
            updates.append(service)
        ordered.append(service)
    if updates:
        Service.objects.bulk_update(updates, ["position", "updated_at"])
    return ordered


@transaction.atomic
def move_services(
    services: Iterable[Service] | QuerySet[Service],
    target_location: Location,
) -> list[Service]:
    """
    Move services to ``target_location``, appending in the given order.

    Source locations are renumbered so positions stay dense. Services already
    in ``target_location`` are left in place and not duplicated.
    """
    to_move = _resolve_services(services)
    if not to_move:
        return []

    source_ids = {service.location_id for service in to_move}
    list(
        Location.objects.select_for_update().filter(
            pk__in={target_location.pk, *source_ids}
        )
    )
    # Lock all services in every involved location so append positions stay unique.
    for location_id in {target_location.pk, *source_ids}:
        list(
            Service.objects.select_for_update()
            .filter(location_id=location_id)
            .order_by(*SERVICE_ORDER)
        )
    locked_movers = list(
        Service.objects.select_for_update()
        .filter(pk__in=[service.pk for service in to_move])
        .order_by("pk")
    )
    by_pk = {service.pk: service for service in locked_movers}
    ordered_movers = [by_pk[service.pk] for service in to_move if service.pk in by_pk]

    already_here = [
        service
        for service in ordered_movers
        if service.location_id == target_location.pk
    ]
    relocating = [
        service
        for service in ordered_movers
        if service.location_id != target_location.pk
    ]
    if not relocating:
        return already_here

    next_position = _next_position_locked(target_location)
    now = timezone.now()
    updates: list[Service] = []
    for offset, service in enumerate(relocating):
        service.location = target_location
        service.position = next_position + offset
        service.updated_at = now
        updates.append(service)
    Service.objects.bulk_update(updates, ["location", "position", "updated_at"])

    for location_id in source_ids - {target_location.pk}:
        _renumber_services(
            list(
                Service.objects.filter(location_id=location_id).order_by(*SERVICE_ORDER)
            )
        )

    return relocating


@transaction.atomic
def duplicate_service(service: Service) -> Service:
    """
    Create a copy of ``service`` at the end of the same location.

    Slug is left blank so ``Service.save`` generates a unique value. Logo file
    storage is shared (same path) when present.
    """
    location = _lock_location(service.location)
    _lock_location_services(location)
    return Service.objects.create(
        location=location,
        name=service.name,
        url=service.url,
        description=service.description,
        logo=service.logo.name if service.logo else "",
        active=service.active,
        open_in_new_tab=service.open_in_new_tab,
        position=_next_position_locked(location),
        slug="",
    )


@transaction.atomic
def duplicate_services(
    services: Iterable[Service] | QuerySet[Service],
) -> list[Service]:
    """Duplicate each service at the end of its current location."""
    return [duplicate_service(service) for service in _resolve_services(services)]


def set_services_active(
    services: Iterable[Service] | QuerySet[Service],
    active: bool,
) -> int:
    """Set ``active`` on the given services. Returns the number of rows updated."""
    if isinstance(services, QuerySet):
        return services.update(active=active)

    ids = [service.pk for service in services if service.pk is not None]
    if not ids:
        return 0
    return Service.objects.filter(pk__in=ids).update(active=active)


@transaction.atomic
def delete_service(service: Service) -> None:
    """Delete ``service`` and renumber remaining siblings densely."""
    location = _lock_location(service.location)
    siblings = _lock_location_services(location)
    target = next((item for item in siblings if item.pk == service.pk), None)
    if target is None:
        return
    remaining = [item for item in siblings if item.pk != service.pk]
    Service.objects.filter(pk=target.pk).delete()
    _renumber_services(remaining)


def _ordered_siblings(service: Service) -> list[Service]:
    return list(
        Service.objects.select_for_update()
        .filter(location_id=service.location_id)
        .order_by(*SERVICE_ORDER)
    )


def _swap_positions(first: Service, second: Service) -> None:
    first.position, second.position = second.position, first.position
    now = timezone.now()
    first.updated_at = now
    second.updated_at = now
    Service.objects.bulk_update([first, second], ["position", "updated_at"])


@transaction.atomic
def move_service_up(service: Service) -> Service:
    """Swap ``service`` with the previous sibling, if any."""
    siblings = _ordered_siblings(service)
    index = next(i for i, item in enumerate(siblings) if item.pk == service.pk)
    if index == 0:
        return siblings[0]
    _swap_positions(siblings[index - 1], siblings[index])
    _renumber_services(
        list(
            Service.objects.filter(location_id=service.location_id).order_by(
                *SERVICE_ORDER
            )
        )
    )
    service.refresh_from_db()
    return service


@transaction.atomic
def move_service_down(service: Service) -> Service:
    """Swap ``service`` with the next sibling, if any."""
    siblings = _ordered_siblings(service)
    index = next(i for i, item in enumerate(siblings) if item.pk == service.pk)
    if index >= len(siblings) - 1:
        return siblings[index]
    _swap_positions(siblings[index], siblings[index + 1])
    _renumber_services(
        list(
            Service.objects.filter(location_id=service.location_id).order_by(
                *SERVICE_ORDER
            )
        )
    )
    service.refresh_from_db()
    return service


@transaction.atomic
def move_service_to_top(service: Service) -> Service:
    """Move ``service`` to position 0 within its location."""
    siblings = _ordered_siblings(service)
    index = next(i for i, item in enumerate(siblings) if item.pk == service.pk)
    if index == 0:
        return siblings[0]
    item = siblings.pop(index)
    siblings.insert(0, item)
    _renumber_services(siblings)
    service.refresh_from_db()
    return service


@transaction.atomic
def move_service_to_bottom(service: Service) -> Service:
    """Move ``service`` to the last position within its location."""
    siblings = _ordered_siblings(service)
    index = next(i for i, item in enumerate(siblings) if item.pk == service.pk)
    if index >= len(siblings) - 1:
        return siblings[index]
    item = siblings.pop(index)
    siblings.append(item)
    _renumber_services(siblings)
    service.refresh_from_db()
    return service
