"""Correct the double-escaped kicker on the seeded news page hero.

The seed file stored ``News &amp;amp; media`` in the hero HTML and an HTML
entity in the section's ``kicker`` setting. Both render as literal
``&amp;`` text. This migration corrects only those exact values on the
seed-origin ``news`` page; other pages and dashboard-created content are
left untouched.
"""

from django.db import migrations

OLD_HTML_KICKER = "News &amp;amp; media"
NEW_HTML_KICKER = "News &amp; media"
OLD_SETTINGS_KICKER = "News &amp; media"
NEW_SETTINGS_KICKER = "News & media"


def fix_news_kicker(apps, schema_editor):
    Page = apps.get_model("content", "Page")
    for page in Page.objects.filter(slug="news"):
        for section in page.sections.filter(label="Page hero"):
            update_fields = []
            html = section.html or ""
            if OLD_HTML_KICKER in html:
                section.html = html.replace(OLD_HTML_KICKER, NEW_HTML_KICKER)
                update_fields.append("html")
            settings = section.settings or {}
            if settings.get("kicker") == OLD_SETTINGS_KICKER:
                section.settings = {**settings, "kicker": NEW_SETTINGS_KICKER}
                update_fields.append("settings")
            if update_fields:
                section.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0017_section_seed_key"),
    ]

    operations = [
        migrations.RunPython(fix_news_kicker, migrations.RunPython.noop),
    ]
