# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-01-18 12:07
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('links', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='link',
            name='shorten_url',
        ),
    ]