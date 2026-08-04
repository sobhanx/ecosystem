# Development guide

English maintainer documentation for the `ecosystem` Django package.

Editor-facing Admin localization is Persian; this file stays English.

## Local setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]" 2>/dev/null || pip install -e .
pip install build Pillow
```

Editable install requires Django 5.2+ and Pillow.

## Testing

Run the full package suite (in-memory SQLite, no demo database required):

```bash
python scripts/runtests.py
```

Coverage focuses on:

- Template tag compatibility (`{% ecosystem "footer" %}`)
- Lookups and write helpers (ordering, moves, deletes)
- Admin workspace and ServiceAdmin behavior
- Permissions, packaging (wheel/sdist), migrations, and Persian catalogs

Do not rely on test execution order. Prefer observable behavior over brittle
HTML snapshots.

## Demo workflow

The `demo/` project is the product laboratory. It is **not** included in the
published wheel.

```bash
pip install -e .
cd demo
python manage.py migrate
python manage.py loaddata sample_services
python manage.py ensuresuperuser
python manage.py runserver
```

| URL | Purpose |
|---|---|
| http://127.0.0.1:8000/ | Template tag rendering for `header`, `main`, `footer` |
| http://127.0.0.1:8000/admin/ | Editor experience (Locations → workspace) |

Default superuser (created only when none exists): `admin` / `admin`.

See [demo/README.md](demo/README.md) for login, workspace navigation, and
optional Persian Admin checks.

## Architecture reminders

```text
models
  ↑
lookups  →  templatetags
  ↑
services  →  admin
```

- Reads live in `lookups.py`
- Mutations live in `services.py`
- Admin orchestrates only
- Do not put ordering logic in `Model.save()`

Public compatibility surfaces hosts may import:

```python
from ecosystem.lookups import get_active_services   # preferred
from ecosystem.services import get_active_services  # re-export
from ecosystem.admin import LocationAdmin, ServiceAdmin
```

Template contract remains `{% ecosystem "footer" %}`.

## Release process

1. Ensure `python scripts/runtests.py` is green.
2. Update [CHANGELOG.md](CHANGELOG.md) for the release.
3. Bump version in `pyproject.toml` and `__init__.py`.
4. Clear stale artifacts: `rm -rf dist build *.egg-info`
5. Build: `python -m build`
6. Verify the wheel contains `admin/`, `migrations/`, `templates/`, `static/`,
   `locale/`, `lookups.py`, and `services.py`.
7. Clean-install smoke test:

   ```bash
   python -m pip install --no-deps --target /tmp/eco-check dist/ecosystem-*.whl
   PYTHONPATH=/tmp/eco-check python -c "import ecosystem; print(ecosystem.__version__)"
   ```

8. Publish or copy the wheel to the internal index.
9. Roll hosts: install → `migrate ecosystem` → `collectstatic` if needed →
   smoke Admin + `{% ecosystem %}`.

Also see [UPGRADING.md](UPGRADING.md) for host upgrade notes.
