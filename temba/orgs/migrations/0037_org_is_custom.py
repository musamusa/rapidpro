# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-10-06 01:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0036_ensure_anon_user_exists'),
    ]

    operations = [
        migrations.AddField(
            model_name='org',
            name='is_custom',
            field=models.BooleanField(default=False, help_text='If this organization has custom configurations', verbose_name='Custom'),
        ),
    ]