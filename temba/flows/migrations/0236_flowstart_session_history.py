# Generated by Django 2.2.10 on 2020-07-22 21:31

from django.db import migrations

import temba.utils.json
import temba.utils.models


class Migration(migrations.Migration):

    dependencies = [("flows", "0235_flow_ticketer_dependencies")]

    operations = [
        migrations.AddField(
            model_name="flowstart",
            name="session_history",
            field=temba.utils.models.JSONField(encoder=temba.utils.json.TembaEncoder, null=True),
        )
    ]
