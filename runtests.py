#!/usr/bin/env python
"""Standalone test runner for the ecosystem reusable Django app."""

from __future__ import annotations

import os
import sys


def main() -> None:
    """Configure a minimal Django project and run the app test suite."""
    import django
    from django.conf import settings

    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Package lives at <parent>/ecosystem/; parent must be on sys.path.
    sys.path.insert(0, os.path.dirname(base_dir))

    if not settings.configured:
        settings.configure(
            DEBUG=True,
            SECRET_KEY="ecosystem-test-secret-key-not-for-production",
            ROOT_URLCONF="ecosystem.urls",
            INSTALLED_APPS=[
                "django.contrib.admin",
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                "ecosystem",
            ],
            MIDDLEWARE=[
                "django.middleware.security.SecurityMiddleware",
                "django.contrib.sessions.middleware.SessionMiddleware",
                "django.middleware.common.CommonMiddleware",
                "django.middleware.csrf.CsrfViewMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
                "django.contrib.messages.middleware.MessageMiddleware",
            ],
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "APP_DIRS": True,
                    "OPTIONS": {
                        "context_processors": [
                            "django.template.context_processors.request",
                            "django.contrib.auth.context_processors.auth",
                            "django.contrib.messages.context_processors.messages",
                        ],
                    },
                }
            ],
            LANGUAGE_CODE="en-us",
            TIME_ZONE="UTC",
            USE_I18N=True,
            USE_TZ=True,
            STATIC_URL="/static/",
            MEDIA_URL="/media/",
            MEDIA_ROOT=os.path.join(base_dir, "media"),
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        )

    django.setup()

    from django.core.management import call_command

    call_command("test", "ecosystem", verbosity=2)


if __name__ == "__main__":
    main()
