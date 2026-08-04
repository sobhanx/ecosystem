# django-ecosystem

Reusable Django application for managing external services that share one product
ecosystem (for example `academy.example.com`, `shop.example.com`,
`blog.example.com`).

**Locations** are the editorial aggregate root. Editors manage each placement
(footer, header, …) from a dedicated **Location workspace** in Django Admin.
Templates still render with the same inclusion tag.

The package makes **no assumptions** about the host project beyond standard
Django settings (`INSTALLED_APPS`, media, and migrations).

## Requirements

- Python 3.10+
- Django 5.2+
- [Pillow](https://pillow.readthedocs.io/) (required by Django for `ImageField`)

## Installation

Prefer an exact version pin from a freshly built wheel or your internal index:

```bash
pip install ecosystem==2.1.0
# or from a path / wheel file
pip install /path/to/ecosystem-2.1.0-py3-none-any.whl
```

```python
INSTALLED_APPS = [
    # ...
    "ecosystem",
]
```

Then:

```bash
python manage.py migrate ecosystem
python manage.py collectstatic  # when you collect app static files in production
```

See [UPGRADING.md](UPGRADING.md) for 1.x → 2.x notes and the release process.
See [CHANGELOG.md](CHANGELOG.md) for version history.

## Location-first workflow

1. Open **Ecosystem → Locations**.
2. Create a location with a stable **key** (for example `footer`) and a clear name.
3. Open the **workspace** for that location.
4. Quick-add services, drag to reorder (or use move buttons), activate/hide,
   duplicate, or move services between locations.
5. Leave detailed edits (logo, description, slug) to the service change form when needed.

`ServiceAdmin` remains available for global search and rare edits. Prefer the
workspace for day-to-day ordering and activation. Changing a service’s location
in ServiceAdmin keeps dense order on both placements.

**Key contract:** `Location.key` is the public template identifier. Surrounding
whitespace is trimmed on save. Changing an existing key is a breaking change for
every `{% ecosystem "key" %}` call that still uses the old value.

**Ordering:** Service order within a location is system-managed. Editors reorder
from the location workspace; Admin forms do not expose editable positions.

## Template tag (unchanged API)

Location keys are free-form strings that must match `Location.key`
(case-sensitive, after trimming surrounding whitespace):

```django
{% load ecosystem %}

{% ecosystem "footer" %}
{% ecosystem "pricing_page" %}
```

Only **active** services on an **active** location are returned, ordered by
position, then primary key. Missing or inactive locations render an empty list.

Legacy alias (still supported):

```django
{% ecosystem_services "footer" %}
```

## Configuration

| Setting | Purpose |
|---|---|
| `INSTALLED_APPS` | Register the app |
| `MEDIA_URL` / `MEDIA_ROOT` | Serve uploaded logos |
| Database | Store `Location` and `Service` rows |
| `ECOSYSTEM_LOCATIONS` (optional) | **Migration-time labels only** for keys already present on 1.x services during `0004`. Does not create locations or drive Admin UI at runtime. |

## Media configuration

Logos are stored under `MEDIA_ROOT/ecosystem/services/`.

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

Serve `MEDIA_ROOT` in development or via your reverse proxy in production.

## Overriding templates

Default inclusion template: `ecosystem/services.html`.

Override it in the host project with the same relative path. The tag provides a
`services` queryset (logo, name, link; `open_in_new_tab` respected).

## Internationalization

Admin labels use `gettext_lazy`. Persian translations ship in `locale/fa/`.

## Project structure

```text
ecosystem/                  # repository root (importable Django app)
  models.py                 # Location + Service
  services.py               # Write API (ordering, activate, duplicate, …)
  lookups.py                # Read helpers for template rendering
  admin.py                  # Location-first Admin + workspace
  templates/admin/ecosystem/
    location_workspace.html
  static/ecosystem/         # SortableJS + workspace/admin helpers
  templatetags/ecosystem.py
  locale/fa/
  migrations/
  tests/
  scripts/runtests.py
  demo/                     # Local QA project (not packaged)
```

## Running package tests

```bash
python scripts/runtests.py
```

## Development demo

```bash
pip install -e .
cd demo
python manage.py migrate
python manage.py loaddata sample_services
python manage.py ensuresuperuser
python manage.py runserver
```

- Homepage: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

Default demo superuser (created only when none exists): `admin` / `admin`.

## License

MIT
