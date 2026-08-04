# Ecosystem demo

Local product laboratory for the `ecosystem` package. **Not** included in the
published wheel.

## Quick start

From the repository root:

```bash
pip install -e .
cd demo
python manage.py migrate
python manage.py loaddata sample_services
python manage.py ensuresuperuser
python manage.py runserver
```

| URL | What to look at |
|---|---|
| http://127.0.0.1:8000/ | Template rendering for Header / Main / Footer |
| http://127.0.0.1:8000/admin/ | Editor experience |

Default superuser (created only when none exists): `admin` / `admin`.

## Editor workflow (Admin)

1. Sign in at `/admin/`.
2. Open **Ecosystem → Locations**.
3. Choose **Header**, **Main**, or **Footer**.
4. Click **Open workspace**.
5. Quick-add a service, drag to reorder (or use move buttons), hide/show, or
   duplicate.
6. Reload the homepage and confirm `{% ecosystem "…" %}` reflects the change.

This is the intended product loop: **choose a location → manage services →
templates update**.

## Sample data

The `sample_services` fixture creates:

| Location key | Sample services |
|---|---|
| `header` | Academy, Shop, Dashboard |
| `main` | Documentation, Support |
| `footer` | Blog, Status, Careers (hidden example) |

Use the footer **Careers** row to see inactive services omitted from the public
template while remaining visible in the workspace.

## Persian Admin

Persian is the **fixed** Admin language (`LANGUAGE_CODE = "fa"`).

Ecosystem ships `locale/fa/LC_MESSAGES/django.mo`. Django’s own Admin catalog
for `fa` is also used.

Activation requirements:

1. `USE_I18N = True`
2. `LANGUAGE_CODE = "fa"`
3. **Do not** enable `LocaleMiddleware` in this demo unless you intentionally
   want browser `Accept-Language` (usually `en-US`) to override Persian for
   `/admin/` requests. That mismatch is why the shell can show Persian while
   Admin stays English.

There is no `/fa/admin/` prefix: the demo does not use `i18n_patterns`.
Language comes from `LANGUAGE_CODE`, not from the URL path.

Catalog spot-check:

```bash
cd demo
python manage.py shell -c "from django.utils.translation import gettext as _; print(_('Ecosystem'), _('location'), _('Add'))"
```

After changing language settings, restart `runserver` and use a fresh browser
tab (clear `django_language` cookie if an old English cookie remains from an
earlier LocaleMiddleware experiment).

## Notes

- Media uploads land under `demo/media/`.
- `ECOSYSTEM_LOCATIONS` in demo settings is migration-label metadata only; Admin
  locations come from the database / fixtures.
- See [DEVELOPMENT.md](../DEVELOPMENT.md) for package tests and release steps.
