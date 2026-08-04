# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Write API in `services.py` and read helpers in `lookups.py` (originally
  introduced as `selectors.py` in 2.0 development).
- Migration `0004_location_and_service_fk` from string locations to FK + `position`.

### Changed

- Template tag API remains `{% ecosystem "key" %}` (key matches `Location.key`).
- `Service.location` is a ForeignKey; `display_order` replaced by `position`.

## [1.1.1] — prior

- String-based service locations and Django Admin Service-centric workflow.
