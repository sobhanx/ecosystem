"""URL configuration for the ecosystem application.

No public URL patterns are registered. Host projects consume services via the
``{% ecosystem %}`` template tag (or the legacy ``{% ecosystem_services %}``
alias).
"""

from __future__ import annotations

app_name = "ecosystem"

urlpatterns: list = []
