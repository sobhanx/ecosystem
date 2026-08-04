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

## Persian Admin (optional)

Demo defaults to English (`LANGUAGE_CODE = "en-us"`) so everyday development
stays predictable. To preview the Persian Admin UI:

1. In `demo/config/settings.py`, temporarily set:

   ```python
   LANGUAGE_CODE = "fa"
   ```

2. Ensure `USE_I18N = True` (already on).
3. Restart `runserver` and open `/admin/`.
4. Confirm labels such as محل نمایش, سرویس, ترتیب, and workspace wording.

Revert `LANGUAGE_CODE` when you are done so package tests and English docs stay
easy to use.

Alternatively, keep `en-us` and use Django’s language activation in a throwaway
shell/session when spot-checking catalogs.

## Notes

- Media uploads land under `demo/media/`.
- `ECOSYSTEM_LOCATIONS` in demo settings is migration-label metadata only; Admin
  locations come from the database / fixtures.
- See [DEVELOPMENT.md](../DEVELOPMENT.md) for package tests and release steps.
