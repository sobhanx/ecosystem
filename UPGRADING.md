# Upgrading django-ecosystem

## 1.x → 2.0

Version **2.0** introduces a first-class **Location** model and a Location-centric
Admin workspace. The public template tag API is unchanged.

### What changed

| Area | 1.x | 2.0 |
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

Migration `0004_location_and_service_fk` (shipped with the Location work):

1. Creates the `Location` table.
2. Creates a `Location` for each distinct legacy string key on services.
3. Points services at those locations and copies order into `position`.
4. Removes the old string column and `display_order`.

Run:

```bash
python manage.py migrate ecosystem
```

No manual rewrite of service rows is required for a normal 1.x database.

### Admin workflow

1. Prefer **Ecosystem → Locations**.
2. Use **Open workspace** to add, reorder (drag or buttons), activate, duplicate,
   and move services.
3. Use **Service** admin for global search and detailed field edits.

Ordering must go through the workspace / service layer. Editors should not type
positions by hand.

### Optional `ECOSYSTEM_LOCATIONS`

In 1.x this setting fed a free-form location string widget. In 2.x it only
provides suggested **labels** for keys that already exist; it does **not**
auto-create Location rows on migrate (to avoid fixture clashes). Create
locations in Admin (or fixtures) explicitly.

### Breaking notes for host code

- Do not filter services with `location="footer"` as a string. Use
  `location__key="footer"` or `selectors.get_active_services("footer")`.
- Direct writes to `position` outside `ecosystem.services` can leave gaps;
  use `reorder_services`, nudge helpers, or the workspace.
- Package version is **2.0.0**. Pin accordingly if you install from a private
  index or editable path.

### After upgrade checklist

- [ ] `migrate ecosystem`
- [ ] Confirm Locations exist for each template key you use
- [ ] Open each location workspace and verify order
- [ ] Spot-check `{% ecosystem "…" %}` on a staging page
- [ ] Update any host code that assumed string `Service.location`
