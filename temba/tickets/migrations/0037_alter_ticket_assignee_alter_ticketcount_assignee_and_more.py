# Generated by Django 4.0.4 on 2022-05-16 23:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orgs", "0096_user"),
        ("tickets", "0036_backfill_ticket_reply_timings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ticket",
            name="assignee",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, related_name="assigned_tickets", to="orgs.user"
            ),
        ),
        migrations.AlterField(
            model_name="ticketcount",
            name="assignee",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ticket_counts", to="orgs.user"
            ),
        ),
        migrations.AlterField(
            model_name="ticketevent",
            name="assignee",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ticket_assignee_events",
                to="orgs.user",
            ),
        ),
    ]
