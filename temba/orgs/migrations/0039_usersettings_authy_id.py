# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2020-03-03 17:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0038_creditalert_admins'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='authy_id',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Authy ID'),
        ),
    ]