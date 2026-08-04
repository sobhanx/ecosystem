"""Write operations and compatibility exports for ecosystem services.

Read lookups live in ``ecosystem.selectors``. This module owns mutations used by
Admin (and tests) so ordering rules stay consistent in one place.

``get_active_services`` is re-exported for backward compatibility.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet

from .models import Location, Service
from .selectors import get_active_services

__all__ = [
    "get_active_services",
    "quick_add_service",
    "reorder_services",
    "move_services",
    "duplicate_service",
    "set_services_active",
    "delete_service",
    "move_service_up",
    "move_service_down",
    "move_service_to_top",
    "move_service_to_bottom",
]


def _services_for_location(location: Location) -> QuerySet[Service]:
    return Service.objects.filter(location=location).order_by("position", "pk")


def _next_position(location: Location) -> int:
    """Return the next append position assuming dense ordering."""
    return _services_for_location(location).count()


def _renumber_location(location: Location) -> None:
    """Rewrite dense ``position`` values ``0..n-1`` for ``location``."""
    services = list(_services_for_location(location))
    updates: list[Service] = []
    for index, service in enumerate(services):
        if service.position != index:
            service.position = index
            updates.append(service)
    if updates:
        Service.objects.bulk_update(updates, ["position"])


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

    return Service.objects.create(
        location=location,
        name=name,
        url=url,
        position=_next_position(location),
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

    locked = list(
        Service.objects.select_for_update()
        .filter(location=location)
        .order_by("position", "pk")
    )
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
    for index, pk in enumerate(ids):
        service = by_id[pk]
        if service.position != index:
            service.position = index
            updates.append(service)
        ordered.append(service)
    if updates:
        Service.objects.bulk_update(updates, ["position"])
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

    # Lock target and all source locations involved.
    source_ids = {service.location_id for service in to_move}
    list(
        Location.objects.select_for_update().filter(
            pk__in={target_location.pk, *source_ids}
        )
    )
    list(
        Service.objects.select_for_update().filter(
            pk__in=[service.pk for service in to_move]
        )
    )

    already_here = [
        service for service in to_move if service.location_id == target_location.pk
    ]
    relocating = [
        service for service in to_move if service.location_id != target_location.pk
    ]
    if not relocating:
        return already_here

    next_position = _next_position(target_location)
    updates: list[Service] = []
    for offset, service in enumerate(relocating):
        service.location = target_location
        service.position = next_position + offset
        updates.append(service)
    Service.objects.bulk_update(updates, ["location", "position"])

    for location_id in source_ids - {target_location.pk}:
        _renumber_location(Location.objects.get(pk=location_id))

    return relocating


@transaction.atomic
def duplicate_service(service: Service) -> Service:
    """
    Create a copy of ``service`` at the end of the same location.

    Slug is left blank so ``Service.save`` generates a unique value. Logo file
    storage is shared (same path) when present.
    """
    return Service.objects.create(
        location=service.location,
        name=service.name,
        url=service.url,
        description=service.description,
        logo=service.logo.name if service.logo else "",
        active=service.active,
        open_in_new_tab=service.open_in_new_tab,
        position=_next_position(service.location),
        slug="",
    )


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
    location = service.location
    service.delete()
    _renumber_location(location)


def _ordered_siblings(service: Service) -> list[Service]:
    return list(
        Service.objects.select_for_update()
        .filter(location_id=service.location_id)
        .order_by("position", "pk")
    )


def _swap_positions(first: Service, second: Service) -> None:
    first.position, second.position = second.position, first.position
    Service.objects.bulk_update([first, second], ["position"])


@transaction.atomic
def move_service_up(service: Service) -> Service:
    """Swap ``service`` with the previous sibling, if any."""
    siblings = _ordered_siblings(service)
    index = next(i for i, item in enumerate(siblings) if item.pk == service.pk)
    if index == 0:
        return siblings[0]
    _swap_positions(siblings[index - 1], siblings[index])
    _renumber_location(service.location)
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
    _renumber_location(service.location)
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
    updates: list[Service] = []
    for position, sibling in enumerate(siblings):
        if sibling.position != position:
            sibling.position = position
            updates.append(sibling)
    if updates:
        Service.objects.bulk_update(updates, ["position"])
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
    updates: list[Service] = []
    for position, sibling in enumerate(siblings):
        if sibling.position != position:
            sibling.position = position
            updates.append(sibling)
    if updates:
        Service.objects.bulk_update(updates, ["position"])
    service.refresh_from_db()
    return service
