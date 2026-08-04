"""Django Admin package for ecosystem locations and services.

Importing this package registers ``LocationAdmin`` and ``ServiceAdmin`` with
the default admin site (same behavior as the former monolithic ``admin.py``).
"""

from __future__ import annotations

from .location import LocationAdmin
from .service import ServiceAdmin

__all__ = [
    "LocationAdmin",
    "ServiceAdmin",
]
