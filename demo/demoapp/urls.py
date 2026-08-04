"""URL routes for the demo application."""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "demoapp"

urlpatterns = [
    path("", views.home, name="home"),
]
