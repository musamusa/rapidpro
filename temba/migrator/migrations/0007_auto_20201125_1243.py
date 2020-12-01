# Generated by Django 2.2.4 on 2020-11-25 12:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("migrator", "0006_auto_20200605_1857")]

    operations = [
        migrations.AddField(
            model_name="migrationtask",
            name="migration_related_uuid",
            field=models.CharField(help_text="The UUID of the related migration", max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="migrationtask",
            name="start_from",
            field=models.IntegerField(default=0, help_text="Step to start from", null=True),
        ),
        migrations.AlterField(
            model_name="migrationassociation",
            name="model",
            field=models.CharField(
                choices=[
                    ("campaigns_campaign", "campaigns_campaign"),
                    ("campaigns_campaignevent", "campaigns_campaignevent"),
                    ("channels_channel", "channels_channel"),
                    ("contacts_contact", "contacts_contact"),
                    ("contacts_contacturn", "contacts_contacturn"),
                    ("contacts_contactgroup", "contacts_contactgroup"),
                    ("contacts_contactfield", "contacts_contactfield"),
                    ("msgs_msg", "msgs_msg"),
                    ("msgs_label", "msgs_label"),
                    ("msgs_broadcast", "msgs_broadcast"),
                    ("flows_flow", "flows_flow"),
                    ("flows_flowlabel", "flows_flowlabel"),
                    ("flows_flowrun", "flows_flowrun"),
                    ("flows_flowstart", "flows_flowstart"),
                    ("links_link", "links_link"),
                    ("schedules_schedule", "schedules_schedule"),
                    ("orgs_org", "orgs_org"),
                    ("orgs_topups", "orgs_topups"),
                    ("orgs_language", "orgs_language"),
                    ("triggers_trigger", "triggers_trigger"),
                    ("api_resthook", "api_resthook"),
                    ("api_webhookevent", "api_webhookevent"),
                ],
                max_length=255,
                verbose_name="Model related to the ID",
            ),
        ),
    ]