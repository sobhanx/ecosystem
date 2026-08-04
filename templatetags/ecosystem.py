"""Template tags for rendering ecosystem services."""

from __future__ import annotations

from django import template
from django.db.models import QuerySet

from ..models import Service
from ..lookups import get_active_services

register = template.Library()

_TEMPLATE = "ecosystem/services.html"


def _services_context(location: str) -> dict[str, QuerySet[Service]]:
    """Build inclusion-tag context via the shared query layer (one query)."""
    return {"services": get_active_services(location)}


@register.inclusion_tag(_TEMPLATE)
def ecosystem(location: str) -> dict[str, QuerySet[Service]]:
    """
    Render active services for the given placement location.

    Usage::

        {% load ecosystem %}
        {% ecosystem "footer" %}
        {% ecosystem "pricing_page" %}
        {% ecosystem "article_bottom" %}

    The inclusion template receives a single ``services`` queryset. Django
    evaluates it once when the template iterates.
    """
    return _services_context(location)


@register.inclusion_tag(_TEMPLATE)
def ecosystem_services(location: str) -> dict[str, QuerySet[Service]]:
    """
    Deprecated alias for :func:`ecosystem`.

    Kept so existing templates continue to work::

        {% load ecosystem %}
        {% ecosystem_services "footer" %}
    """
    return _services_context(location)
