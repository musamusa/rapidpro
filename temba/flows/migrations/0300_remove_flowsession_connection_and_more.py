# Generated by Django 4.0.7 on 2022-09-28 17:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("flows", "0299_session_status_trigger"),
        ("ivr", "0021_convert_connections"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="flowsession",
            name="connection",
        ),
        migrations.RemoveField(
            model_name="flowstart",
            name="connections",
        ),
    ]