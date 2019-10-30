# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2019-07-16 22:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('msgs', '0112_auto_20190711_2137'),
    ]

    operations = [
        migrations.AddField(
            model_name='msg',
            name='read_on',
            field=models.DateTimeField(blank=True, help_text='Date that the message was read by the WhatsApp contact', null=True),
        ),
    ]