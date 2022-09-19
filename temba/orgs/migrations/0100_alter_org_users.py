# Generated by Django 4.0.4 on 2022-06-16 16:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orgs", "0099_backfill_org_membership"),
    ]

    operations = [
        migrations.AlterField(
            model_name="org",
            name="users",
            field=models.ManyToManyField(related_name="orgs", through="orgs.OrgMembership", to="orgs.user"),
        ),
    ]
