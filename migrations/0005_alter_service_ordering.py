# Generated manually for Ecosystem 2.1 ordering tie-break consistency.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ecosystem", "0004_location_and_service_fk"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="service",
            options={
                "ordering": ("position", "pk"),
                "verbose_name": "service",
                "verbose_name_plural": "services",
            },
        ),
    ]
