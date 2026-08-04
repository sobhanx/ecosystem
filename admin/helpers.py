"""Reusable Django Admin presentation helpers for ecosystem."""

from __future__ import annotations

from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html


def boolean_badge(value: bool, *, yes: str, no: str) -> str:
    """Render a compact active/hidden badge."""
    if value:
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
            "background:#e7f8ed;color:#0b6b2f;font-size:12px;font-weight:600;"
            '">{}</span>',
            yes,
        )
    return format_html(
        '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
        "background:#f4f4f4;color:#666;font-size:12px;font-weight:600;"
        '">{}</span>',
        no,
    )


def workspace_url(location_id: int) -> str:
    try:
        return reverse("admin:ecosystem_location_workspace", args=[location_id])
    except NoReverseMatch:
        return f"/admin/ecosystem/location/{location_id}/workspace/"


def reorder_url(location_id: int) -> str:
    try:
        return reverse("admin:ecosystem_location_reorder", args=[location_id])
    except NoReverseMatch:
        return f"/admin/ecosystem/location/{location_id}/reorder/"
