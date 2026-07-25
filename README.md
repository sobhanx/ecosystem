# django-ecosystem

Reusable Django application for managing external services that share one product
ecosystem (for example `academy.example.com`, `shop.example.com`,
`blog.example.com`).

Administrators register services in Django Admin. Templates render them with an
inclusion tag. The package makes **no assumptions** about the host project beyond
standard Django settings (`INSTALLED_APPS`, media, and migrations).

## Requirements

- Python 3.12+
- Django 5.2+
- [Pillow](https://pillow.readthedocs.io/) (required by Django for `ImageField`)

## Installation

Install the package into your environment:

```bash
pip install -e /path/to/ecosystem
```

Or from a built distribution:

```bash
pip install django-ecosystem
```

Add the app to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "ecosystem",
    # or explicitly:
    # "ecosystem.apps.EcosystemConfig",
]
```

## Configuration

Host projects need the usual Django media/database setup. One optional setting
improves the admin location picker:

| Setting | Purpose |
|---|---|
| `INSTALLED_APPS` | Register the app |
| `MEDIA_URL` / `MEDIA_ROOT` | Serve uploaded logos |
| Database | Store `Service` rows |
| `ECOSYSTEM_LOCATIONS` (optional) | Suggested placement keys in admin |

### Optional location suggestions

`Service.location` remains a free-form string. To help editors pick keys without
memorizing them, define suggestions in the host project:

```python
ECOSYSTEM_LOCATIONS = [
    ("footer", "Site footer"),
    ("header", "Site header"),
    ("pricing_page", "Pricing page"),
]
```

Bare strings are also accepted (`["footer", "header"]`). Suggestions are merged
with distinct location values already stored in the database, so previously used
keys stay selectable. The package does **not** ship host-specific location keys.

## Migrations

```bash
python manage.py migrate ecosystem
```

## Media configuration

Logos are stored under `MEDIA_ROOT/ecosystem/services/`.

Example host settings:

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

In development, serve media from `urls.py` as usual:

```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

In production, serve `MEDIA_ROOT` through your reverse proxy or object storage.

## Template tag usage

Location keys are free-form strings. Create any placement in admin, then render it:

```django
{% load ecosystem %}

{% ecosystem "footer" %}
{% ecosystem "pricing_page" %}
{% ecosystem "article_bottom" %}
{% ecosystem "dashboard_left" %}
```

Only **active** services whose `location` matches the given key are returned,
ordered by `display_order`, then `name`.

Legacy alias (still supported):

```django
{% load ecosystem %}
{% ecosystem_services "footer" %}
```

## Overriding templates

Default template path:

```text
ecosystem/services.html
```

Override it in the host project by placing a template with the same relative path
on your template loaders’ search path, for example:

```text
your_project/templates/ecosystem/services.html
```

Keep `APP_DIRS` enabled (or equivalent) so the packaged default remains available
until you override it.

The inclusion tag provides a `services` queryset. Default markup is semantic HTML
only: logo (if set), name, and link. When `open_in_new_tab` is enabled, links use
`target="_blank"` and `rel="noopener noreferrer"`. Output is auto-escaped by
Django’s template engine.

## Admin usage

1. Open **Ecosystem → Services**.
2. Add a service with name, URL, and a placement (location) key.
3. Prefer picking a suggested placement when available; type a new key only when
   introducing a new template-tag location.
4. Optionally upload a logo and set display order.
5. Leave slug blank to auto-generate from the name, or edit it under **Advanced**.
6. Toggle **active** inline on the list page, or use the Activate / Deactivate
   actions on selected rows.

Search covers name, slug, URL, location, and description. Filters cover active
state, open-in-new-tab, location, and updated date. The changelist shows a small
logo thumbnail when a file is present.

## Internationalization

Admin-facing labels, help texts, fieldsets, and actions are wrapped with
`gettext_lazy`. Persian translations ship in `ecosystem/locale/fa/`.

With `LANGUAGE_CODE = "fa"` (and `USE_I18N = True`), Django Admin shows Persian
strings from this app. English message IDs remain the fallback for other
languages.


All rendering lookups go through `ecosystem.services.get_active_services()`.
Template tags call that helper; do not duplicate `active`/`location` filters in
host code if you want consistent behavior.

## Project structure

```text
ecosystem/
  apps.py                 # AppConfig
  models.py               # Service model
  forms.py                # Admin form + location suggestions widget
  admin.py                # Django Admin
  services.py             # Shared queryset helpers
  locale/
    fa/LC_MESSAGES/
      django.po             # Persian translations (source)
      django.mo             # Compiled catalog
  templatetags/
    ecosystem.py          # {% ecosystem %} / legacy alias
  templates/
    ecosystem/
      services.html       # Default inclusion template (overridable)
      widgets/
        location_input.html
  static/
    ecosystem/            # Reserved for future assets
  migrations/
  views.py                # Empty in v1 (no public views)
  urls.py                 # Empty urlpatterns (app_name = "ecosystem")
  tests.py
```

## Running package tests

From the package root:

```bash
python runtests.py
```

## License

MIT
