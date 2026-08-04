# Upgrading django-ecosystem

## Versioning policy

This package follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — incompatible API or data-model changes for hosts
- **MINOR** — backward-compatible hardening and features
- **PATCH** — backward-compatible bug fixes

Pin hosts to an exact version (for example `ecosystem==2.1.0`) when installing
from an internal index or path. After each release, install from a freshly built
wheel — do not reuse stale `dist/` artifacts from older checkouts.

See [CHANGELOG.md](CHANGELOG.md) for release notes and [DEVELOPMENT.md](DEVELOPMENT.md)
for the maintainer release checklist.

## Release process (maintainers)

Follow [DEVELOPMENT.md](DEVELOPMENT.md#release-process). Summary:

1. Ensure tests pass: `python scripts/runtests.py`
2. Bump version in `pyproject.toml` and `__init__.py`
3. Update `CHANGELOG.md`
4. Remove stale build output: `rm -rf dist build *.egg-info`
5. Build: `python -m build`
6. Verify the wheel contains `static/`, `templates/`, `locale/`, `migrations/`,
   `admin/`, and `lookups.py`
7. Publish or copy the new wheel to the internal package index
8. Roll hosts one at a time: install wheel → `migrate ecosystem` → smoke Admin

## 2.1.x → 2.2.0

Backward-compatible documentation, Admin polish, validation, and test maturity
release. No schema migrations.

```bash
pip install --upgrade ecosystem==2.2.0
python manage.py collectstatic  # if you collect app static files
```

Template tag API is unchanged. Prefer the location workspace for day-to-day
editing.

## 2.0.x → 2.1.0

Backward-compatible hardening release.

```bash
pip install --upgrade ecosystem==2.1.0
python manage.py migrate ecosystem
python manage.py collectstatic  # if you collect app static files
```

Notable fixes: ServiceAdmin location moves preserve dense order; append paths
lock under concurrency; packaging includes workspace static assets.

Hosts that imported ``ecosystem.selectors`` in early 2.0 checkouts should switch
to ``ecosystem.lookups`` (same helpers). ``ecosystem.services.get_active_services``
continues to work as a compatibility re-export.

## 1.x → 2.0 / 2.1

Version **2.x** introduces a first-class **Location** model and a Location-centric
Admin workspace. The public template tag API is unchanged.

### What changed

| Area | 1.x | 2.x |
|---|---|---|
| Placement | `Service.location` free-form string | `Service.location` → `Location` FK |
| Ordering field | `display_order` | `position` (dense, system-managed) |
| Primary Admin | Services list | **Locations** + per-location **workspace** |
| Template tag | `{% ecosystem "footer" %}` | Same |

### Template API compatibility

Hosts do **not** need to change templates:

```django
{% load ecosystem %}
{% ecosystem "footer" %}
```

The tag still looks up by location **key**. Inactive or missing locations render
an empty list.

### Data migration

Migration `0004_location_and_service_fk`:

1. Creates the `Location` table.
2. Creates a `Location` for each distinct legacy string key on services.
3. Points services at those locations and copies order into `position`.
4. Removes the old string column and `display_order`.

Run:

```bash
python manage.py migrate ecosystem
```

### Legacy key casing

Early 1.x installs may still store uppercase keys such as `FOOTER` / `HEADER`.
Template tags are **case-sensitive**. After migrate, either:

- update templates to match stored keys, or
- rename `Location.key` values to lowercase in Admin

Mismatch produces an empty render with no error.

### Optional `ECOSYSTEM_LOCATIONS`

This setting is **migration-time only**. During `0004`, it may supply human
labels for keys that already exist on services. It does **not**:

- auto-create Location rows on migrate
- drive Admin widgets or suggestions at runtime

Create locations in Admin (or fixtures) explicitly.

### Breaking notes for host code

- Do not filter services with `location="footer"` as a string. Use
  `location__key="footer"` or `lookups.get_active_services("footer")`.
- Direct writes to `position` outside `ecosystem.services` can leave gaps;
  use `reorder_services`, nudge helpers, or the workspace.
- Changing a service’s location in ServiceAdmin goes through `move_services`
  (2.1+); prefer the workspace for day-to-day moves.

### After upgrade checklist

- [ ] Install a **2.1.x wheel** (not a stale 1.1.1 artifact)
- [ ] `migrate ecosystem`
- [ ] `collectstatic` if applicable
- [ ] Confirm Locations exist for each template key you use
- [ ] Check key casing (`footer` vs `FOOTER`)
- [ ] Open each location workspace and verify order
- [ ] Spot-check `{% ecosystem "…" %}` on a staging page
- [ ] Update any host code that assumed string `Service.location`
