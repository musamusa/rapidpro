# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-08-31 18:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('channels', '0077_auto_20170824_1555'),
    ]

    operations = [
        migrations.AlterField(
            model_name='channelevent',
            name='event_type',
            field=models.CharField(choices=[('unknown', 'Unknown Call Type'), ('mt_call', 'Outgoing Call'), ('mt_miss', 'Missed Outgoing Call'), ('mo_call', 'Incoming Call'), ('mo_miss', 'Missed Incoming Call'), ('new_conversation', 'New Conversation'), ('referral', 'Referral')], help_text='The type of event', max_length=16, verbose_name='Event Type'),
        ),
    ]
