from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("cadastre", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="parcelle",
            name="arpente",
        ),
        migrations.RemoveField(
            model_name="parcelle",
            name="prefixe",
        ),
        migrations.RemoveField(
            model_name="parcelle",
            name="created",
        ),
        migrations.RemoveField(
            model_name="parcelle",
            name="updated",
        ),
        migrations.RemoveField(
            model_name="adresse",
            name="cad_parcelles",
        ),
        migrations.RemoveField(
            model_name="adresse",
            name="lat",
        ),
        migrations.RemoveField(
            model_name="adresse",
            name="lon",
        ),
    ]
