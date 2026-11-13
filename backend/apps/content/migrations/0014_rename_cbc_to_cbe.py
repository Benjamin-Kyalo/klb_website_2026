from django.db import migrations


def rename_cbc_to_cbe(apps, schema_editor):
    DropdownOption = apps.get_model("content", "DropdownOption")
    for opt in DropdownOption.objects.filter(value__icontains="CBC"):
        opt.value = opt.value.replace("CBC", "CBE")
        opt.label = opt.label.replace("CBC", "CBE")
        opt.save(update_fields=["value", "label"])


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0013_unique_backup_filenames"),
    ]

    operations = [
        migrations.RunPython(rename_cbc_to_cbe, migrations.RunPython.noop),
    ]
