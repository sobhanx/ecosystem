"""Views for the ecosystem demo homepage."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    """Render a preview page that exercises several ecosystem placements."""
    return render(request, "home.html")
