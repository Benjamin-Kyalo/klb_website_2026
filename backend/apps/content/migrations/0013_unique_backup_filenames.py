from django.db import migrations, models


def dedupe_backup_records(apps, schema_editor):
    """Keep only the newest history row for each archive filename."""
    BackupRecord = apps.get_model("content", "BackupRecord")
    seen = set()
    for record in BackupRecord.objects.exclude(filename="").order_by(
        "-created_at", "-pk"
    ):
        if record.filename in seen:
            record.delete()
        else:
            seen.add(record.filename)


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0012_backup_and_settings_improvements"),
    ]

    operations = [
        migrations.RunPython(dedupe_backup_records, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="backuprecord",
            constraint=models.UniqueConstraint(
                condition=models.Q(("filename", ""), _negated=True),
                fields=("filename",),
                name="uniq_backup_archive_filename",
            ),
        ),
    ]
