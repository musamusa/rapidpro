# Generated by Django 4.0.6 on 2022-08-02 20:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("msgs", "0180_remove_media_paths_media_status_alter_media_url_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="media",
            name="is_ready",
        ),
    ]
