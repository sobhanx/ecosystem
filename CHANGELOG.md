# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.1] — 2026-08-04

### Fixed

- Workspace nudge helpers (`move_service_up` / `down` / `to_top` / `to_bottom`)
  raise `ValidationError` when the service is no longer in the location, instead
  of an uncaught `StopIteration`.

### Changed

- Documented the public read compatibility surface
  (`ecosystem.services.get_active_services` re-export) in the README.
- Removed a redundant outer `transaction.atomic` on `delete_service` (still
  covered by `delete_services`).

### Migration notes

- No new migrations. Hosts on 2.2.0: install `ecosystem==2.2.1` and restart.
  Template tag and Admin URLs are unchanged.

## [2.2.0] — 2026-08-04

### Added

- Maintainer guide (`DEVELOPMENT.md`) and bilingual README (English for
  developers, Persian product section for editors).
- Demo laboratory guide (`demo/README.md`) with sample Header / Main / Footer
  placements and Persian Admin activation notes.
- Stronger packaging checks (sdist contents, clean-install Django check).
- Broader regression coverage for permissions, ordering, validation, Admin HTTP
  language, and the public template tag.
- Shared test helpers for dense position assertions.

### Changed

- Django Admin split into an `admin` package for maintainability.
- Clearer domain boundaries: `lookups.py` for reads, `services.py` for writes,
  Admin orchestration only.
- Location key validation via `clean()` with documented trim behavior.
- Location workspace UX: one form per row, clearer action groups, clipboard
  fallback feedback, friendlier reorder messages, light mobile layout.
- Persian Admin terminology aligned for locations, services, order, and
  workspace labels.
- Demo Admin language fixed to Persian via `LANGUAGE_CODE = "fa"` (no
  `LocaleMiddleware`, so browser `Accept-Language` cannot override it).

### Fixed

- ServiceAdmin delete paths renumber remaining services densely.
- Reorder and clipboard feedback no longer surface technical internals to
  editors.

### Deprecated

- Nothing.

### Migration notes

- Migration `0006_alter_field_help_texts` updates field help text only (no schema
  shape change).
- Hosts on 2.1.x: install the 2.2.0 wheel, run `migrate ecosystem`, and
  `collectstatic` if you collect app static files.
- Template tag API remains `{% ecosystem "key" %}`.
- For Persian Admin in host projects, set `LANGUAGE_CODE = "fa"`. Prefer not
  enabling `LocaleMiddleware` when Admin language must stay fixed regardless of
  browser language preferences.

## [2.1.0] — 2026-08-04

### Fixed

- Packaging: rebuild artifacts so wheels include static files, admin workspace
  templates, `lookups.py`, locale catalogs, and migrations through `0005`.
- Renamed read module from `selectors.py` to `lookups.py` so packaging no longer
  shadows the Python stdlib `selectors` module when building from the repo root.
- ServiceAdmin location changes now go through `move_services`, preserving dense
  ordering on source and destination locations.
- Append paths (`quick_add_service`, `duplicate_service`, `move_services`) lock
  the location and its services before assigning positions.
- Workspace reorder and bulk-move destinations respect `LocationAdmin.get_queryset`
  and change permission on the target location.
- ServiceAdmin changelist uses `select_related("location")`.
- Delete confirmation no longer embeds translated strings inside inline `onclick`.
- Canonical service order is `(position, pk)` everywhere (models, lookups, admin).

### Changed

- Package version **2.1.0**.
- `ECOSYSTEM_LOCATIONS` documentation clarified: migration-time labels only; it
  does not seed locations or drive Admin suggestions at runtime.
- `bulk_update` position writes also refresh `updated_at`.

### Added

- `CHANGELOG.md` and packaging smoke tests.
- Migration `0005_alter_service_ordering` (options only).

## [2.0.0] — 2026-08-04

### Added

- First-class `Location` model as the editorial aggregate root.
- Location workspace in Django Admin (quick add, nudge, bulk ops, drag-and-drop).
- Write API in `services.py` and read helpers in `lookups.py`.
- Migration `0004_location_and_service_fk` converting string placements to
  Location relationships and system-managed order.

### Changed

- Template tag API remains `{% ecosystem "key" %}` (key matches `Location.key`).
- Service placement is a Location relationship; order uses system-managed
  `position` instead of the former free-form display order field.

## [1.1.1] — prior

- String-based service locations and Django Admin Service-centric workflow.
