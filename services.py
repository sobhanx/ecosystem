"""Compatibility exports for ecosystem read helpers.

Prefer ``ecosystem.selectors`` for new code. This module re-exports the
rendering query helper so existing imports keep working.
"""

from __future__ import annotations

from .selectors import get_active_services

__all__ = ["get_active_services"]
