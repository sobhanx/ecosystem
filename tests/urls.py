"""URLConf used by the package test runner (includes Django Admin)."""

from __future__ import annotations

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
