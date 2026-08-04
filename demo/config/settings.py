"""Django settings for the ecosystem local demo project.

This project is development-only. It is not part of the distributed package.
"""

from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "demo-ecosystem-insecure-secret-key-not-for-production"

DEBUG = True

ALLOWED_HOSTS: list[str] = ["*"] if DEBUG else ["localhost", "127.0.0.1", "[::1]"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "ecosystem",
    "demoapp",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Intentionally no LocaleMiddleware: it would honor browser
    # Accept-Language (usually en-*) and override LANGUAGE_CODE=fa for
    # /admin/ requests. Persian is the fixed Admin language for this demo.
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Persian is the primary (and fixed) Admin language for this product laboratory.
# Do not enable LocaleMiddleware here: browsers typically send
# Accept-Language: en-US, which would activate English for /admin/ even when
# LANGUAGE_CODE is fa. Shell translation checks are not affected by that header.
LANGUAGE_CODE = "fa"
LANGUAGES = [
    ("fa", "Persian"),
]

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Suggested placement keys for the ecosystem admin location picker.
# Optional: used only by historical migration 0004 for labels when upgrading
# from 1.x string locations. Not consumed by Admin or template tags at runtime.
ECOSYSTEM_LOCATIONS = [
    ("header", "Site header"),
    ("main", "Main content"),
    ("footer", "Site footer"),
]
