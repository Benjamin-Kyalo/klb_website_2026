from django.db import migrations


def rename_cbc_to_cbe(apps, schema_editor):
    Book = apps.get_model("catalogue", "Book")
    for book in Book.objects.all():
        changed = False
        for field in ("category", "collection"):
            value = getattr(book, field, "") or ""
            if "CBC" in value:
                setattr(book, field, value.replace("CBC", "CBE"))
                changed = True
        categories = getattr(book, "categories", None)
        if isinstance(categories, list):
            new_categories = [str(item).replace("CBC", "CBE") for item in categories]
            if new_categories != categories:
                book.categories = new_categories
                changed = True
        if changed:
            book.save()


class Migration(migrations.Migration):
    dependencies = [
        ("catalogue", "0003_rename_cbc_to_cbe"),
    ]

    operations = [
        migrations.RunPython(rename_cbc_to_cbe, migrations.RunPython.noop),
    ]
