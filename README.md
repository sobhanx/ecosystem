# django-ecosystem

Reusable Django application for managing **placements** of related product
services (for example Academy, Shop, Blog, Status).

**Core idea:** Ecosystem manages placements, not rows.

A **Location** is a named placement on the site (`footer`, `header`, …).
**Services** are ordered entries inside that placement. Templates consume a
location by its stable **key**:

```django
{% load ecosystem %}
{% ecosystem "footer" %}
```

Django Admin is the product UI. Editors open a location workspace, add and
reorder services, and the template tag renders what visitors see.

The package makes no assumptions about the host beyond standard Django settings
(`INSTALLED_APPS`, media, and migrations).

---

## English — developers

### Requirements

- Python 3.10+
- Django 5.2+
- [Pillow](https://pillow.readthedocs.io/) (required by Django for `ImageField`)

### Installation

Prefer an exact version pin from a freshly built wheel or your internal index:

```bash
pip install ecosystem==2.2.0
# or from a path / wheel file
pip install /path/to/ecosystem-2.2.0-py3-none-any.whl
```

```python
INSTALLED_APPS = [
    # ...
    "ecosystem",
]
```

```bash
python manage.py migrate ecosystem
python manage.py collectstatic  # when you collect app static files in production
```

- Upgrade notes: [UPGRADING.md](UPGRADING.md)
- Release history: [CHANGELOG.md](CHANGELOG.md)
- Maintainer setup, tests, demo, release steps: [DEVELOPMENT.md](DEVELOPMENT.md)

### Concepts

| Concept | Role |
|---|---|
| Location | Aggregate root / placement (`key` matches the template tag) |
| Service | Ordered entry belonging to one location |
| Workspace | Per-location Admin screen for day-to-day editing |
| Template tag | Public render API — unchanged across 2.x |

Service order within a location is system-managed (`0..n-1`). Editors reorder in
the workspace; Admin forms do not expose editable positions.

`Location.key` is the public template contract. Surrounding whitespace is
trimmed on save. Changing an existing key breaks every template that still uses
the old value.

### Template tag

```django
{% load ecosystem %}

{% ecosystem "footer" %}
{% ecosystem "pricing_page" %}
```

Only **active** services on an **active** location are returned, ordered by
position then primary key. Missing or inactive locations render an empty list.

Legacy alias (still supported): `{% ecosystem_services "footer" %}`.

### Configuration

| Setting | Purpose |
|---|---|
| `INSTALLED_APPS` | Register the app |
| `MEDIA_URL` / `MEDIA_ROOT` | Serve uploaded logos |
| Database | Store Location and Service data |
| `ECOSYSTEM_LOCATIONS` (optional) | Migration-time labels only when upgrading from 1.x — not used by Admin at runtime |

Logos are stored under `MEDIA_ROOT/ecosystem/services/`.

### Overriding templates

Default inclusion template: `ecosystem/services.html`. Override it in the host
with the same relative path. The tag provides a `services` queryset.

### Internationalization

- **Admin UI:** ships with Persian translations (`locale/fa/`). Persian is the
  primary Admin language for editors.
- **Developer docs** (this English section, `DEVELOPMENT.md`, `CHANGELOG.md`,
  technical `UPGRADING.md`) stay in English.

### Package layout

```text
ecosystem/                  # repository root (importable Django app)
  models.py
  services.py               # writes / mutations
  lookups.py                # reads for templates
  admin/                    # Location + Service Admin + workspace
  templates/
  static/ecosystem/
  templatetags/ecosystem.py
  locale/fa/
  migrations/
  tests/
  scripts/runtests.py
  demo/                     # local QA project (not packaged)
```

### Tests

```bash
python scripts/runtests.py
```

### License

MIT

---

## فارسی — ویرایشگران و معرفی محصول

**اکوسیستم محل‌های نمایش را مدیریت می‌کند، نه ردیف‌های خام دیتابیس.**

### مفهوم

- **محل نمایش (Location):** جایگاهی در سایت مثل پاورقی، هدر یا صفحه قیمت‌گذاری.
  کلید پایدار (`key`) همان آرگومان تگ قالب است؛ مثلاً `footer`.
- **سرویس (Service):** یک پیوند مرتب‌شده داخل همان محل نمایش (آکادمی، فروشگاه، …).
- **مدیریت سرویس‌های محل نمایش (Workspace):** صفحه اصلی ویرایش در ادمین جنگو
  برای افزودن، مرتب‌سازی، فعال/غیرفعال کردن و تکثیر سرویس‌ها.

بازدیدکننده سایت فقط سرویس‌های **فعال** روی محل نمایش **فعال** را می‌بیند.

### جریان کار در ادمین

1. وارد **Django Admin** شوید.
2. از منوی **اکوسیستم ← محل‌های نمایش** یک محل را انتخاب کنید.
3. **مدیریت سرویس‌های محل نمایش** (Workspace) را باز کنید.
4. سرویس اضافه کنید، با کشیدن یا دکمه‌های جابه‌جایی **ترتیب** را تنظیم کنید،
   نمایش را فعال یا مخفی کنید.
5. در قالب سایت از تگ زیر استفاده کنید (بدون تغییر در API):

```django
{% load ecosystem %}
{% ecosystem "footer" %}
```

زبان رابط ادمین برای ویرایشگران به‌صورت پیش‌فرض فارسی پشتیبانی می‌شود. مستندات
فنی توسعه‌دهندگان به زبان انگلیسی است.
