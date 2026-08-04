# Generated manually for Location FK migration.

from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def _settings_location_labels() -> dict[str, str]:
    """Build key→label map from optional ECOSYSTEM_LOCATIONS setting."""
    labels: dict[str, str] = {}
    for item in getattr(settings, "ECOSYSTEM_LOCATIONS", ()) or ():
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            key, label = str(item[0]).strip(), str(item[1]).strip()
        else:
            key = str(item).strip()
            label = key
        if key and key not in labels:
            labels[key] = label or key
    return labels


def forwards_migrate_locations(apps, schema_editor) -> None:
    """Create Location rows from distinct Service.location strings and link FKs."""
    Location = apps.get_model("ecosystem", "Location")
    Service = apps.get_model("ecosystem", "Service")

    labels = _settings_location_labels()
    keys: dict[str, str] = {}

    for raw in Service.objects.values_list("location", flat=True).distinct():
        key = (raw or "").strip()
        if not key:
            continue
        keys[key] = labels.get(key, key)

    # Only materialize keys that already exist on Service rows. Optional
    # ECOSYSTEM_LOCATIONS labels are applied when present, but settings-only
    # keys are not inserted (avoids clashing with fixtures / later Admin seeds).

    location_by_key: dict[str, object] = {}
    for index, key in enumerate(sorted(keys)):
        location_by_key[key] = Location.objects.create(
            key=key,
            name=keys[key],
            description="",
            active=True,
            position=index,
        )

    for service in Service.objects.all().iterator():
        key = (service.location or "").strip()
        location = location_by_key[key]
        service.location_ref_id = location.pk
        service.position = service.display_order
        service.save(update_fields=["location_ref", "position"])

    for location in Location.objects.all():
        ordered = (
            Service.objects.filter(location_ref=location)
            .order_by("position", "name", "pk")
        )
        for index, service in enumerate(ordered):
            if service.position != index:
                service.position = index
                service.save(update_fields=["position"])


def backwards_migrate_locations(apps, schema_editor) -> None:
    """Restore string location / display_order from Location FK and position."""
    Location = apps.get_model("ecosystem", "Location")
    Service = apps.get_model("ecosystem", "Service")

    key_by_id = dict(Location.objects.values_list("pk", "key"))
    for service in Service.objects.all().iterator():
        service.location = key_by_id.get(service.location_ref_id, "")
        service.display_order = service.position
        service.save(update_fields=["location", "display_order"])


class Migration(migrations.Migration):

    dependencies = [
        ("ecosystem", "0003_optimize_indexes_and_constraints"),
    ]

    operations = [
        migrations.CreateModel(
            name="Location",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        help_text=(
                            'Stable template-tag identifier (for example "footer" '
                            'or "pricing_page"). Prefer leaving this unchanged '
                            "after creation."
                        ),
                        max_length=100,
                        unique=True,
                        verbose_name="key",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text=(
                            'Human-readable label shown in admin '
                            '(for example "Footer").'
                        ),
                        max_length=150,
                        verbose_name="name",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional notes for editors about this placement.",
                        verbose_name="description",
                    ),
                ),
                (
                    "active",
                    models.BooleanField(
                        default=True,
                        help_text=(
                            "Uncheck to hide every service in this placement "
                            "without deleting them."
                        ),
                        verbose_name="active",
                    ),
                ),
                (
                    "position",
                    models.PositiveIntegerField(
                        default=0,
                        help_text=(
                            "Order of this location in admin lists. "
                            "Lower comes first."
                        ),
                        verbose_name="position",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="created at"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="updated at"
                    ),
                ),
            ],
            options={
                "verbose_name": "location",
                "verbose_name_plural": "locations",
                "ordering": ("position", "name"),
            },
        ),
        migrations.AddConstraint(
            model_name="location",
            constraint=models.CheckConstraint(
                condition=models.Q(("key", ""), _negated=True),
                name="ecosystem_location_key_not_empty",
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="location_ref",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="services",
                to="ecosystem.location",
                verbose_name="location",
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="position",
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    "Order within the location. Maintained by the application; "
                    "lower values appear first."
                ),
                verbose_name="position",
            ),
        ),
        migrations.RunPython(
            forwards_migrate_locations,
            backwards_migrate_locations,
        ),
        migrations.RemoveConstraint(
            model_name="service",
            name="ecosystem_svc_location_not_empty",
        ),
        migrations.RemoveIndex(
            model_name="service",
            name="ecosystem_svc_location_idx",
        ),
        migrations.RemoveIndex(
            model_name="service",
            name="ecosystem_svc_lookup_idx",
        ),
        migrations.RemoveField(
            model_name="service",
            name="location",
        ),
        migrations.RemoveField(
            model_name="service",
            name="display_order",
        ),
        migrations.RenameField(
            model_name="service",
            old_name="location_ref",
            new_name="location",
        ),
        migrations.AlterField(
            model_name="service",
            name="location",
            field=models.ForeignKey(
                help_text=(
                    "Placement this service belongs to. Must match a location "
                    "key used in the ecosystem template tag."
                ),
                on_delete=django.db.models.deletion.PROTECT,
                related_name="services",
                to="ecosystem.location",
                verbose_name="location",
            ),
        ),
        migrations.AddIndex(
            model_name="service",
            index=models.Index(
                fields=["location", "position"],
                name="ecosystem_svc_loc_pos_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="service",
            index=models.Index(
                fields=["location", "active", "position"],
                name="ecosystem_svc_loc_active_idx",
            ),
        ),
    ]
