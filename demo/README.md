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

Persian is the **default** Admin language (`LANGUAGE_CODE = "fa"`).

Ecosystem ships `locale/fa/LC_MESSAGES/django.mo`. Django’s own Admin catalog
for `fa` is also used. Activation requires:

1. `USE_I18N = True`
2. `LANGUAGE_CODE = "fa"` (or LocaleMiddleware selecting `fa`)
3. `LocaleMiddleware` after `SessionMiddleware` (enabled in this demo)

To temporarily use English Admin without editing settings, POST to
`/i18n/setlang/` with `language=en` (Django’s built-in language view), or set
your browser/session language to English. Restart is not required for the
cookie-based switch.

Catalog spot-check in a shell:

```bash
cd demo
python manage.py shell -c "from django.utils import translation; from django.utils.translation import gettext as _; translation.activate('fa'); print(_('Ecosystem'), _('location'), _('Workspace'))"
```

## Notes

- Media uploads land under `demo/media/`.
- `ECOSYSTEM_LOCATIONS` in demo settings is migration-label metadata only; Admin
  locations come from the database / fixtures.
- See [DEVELOPMENT.md](../DEVELOPMENT.md) for package tests and release steps.
