# Generated by Django 4.0.4 on 2022-05-10 14:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0166_fix_invalid_names"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contactgroup",
            name="is_system",
            field=models.BooleanField(default=False),
        ),
    ]
