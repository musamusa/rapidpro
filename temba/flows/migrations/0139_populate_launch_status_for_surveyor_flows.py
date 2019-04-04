# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def populate_flow_launch_status(Org, Flow):
    orgs = Org.objects.all().only('pk')
    for org in orgs:
        print('> Updating surveyor flows for %s' % org.slug)
        Flow.objects.filter(org=org, flow_type='S').update(launch_status='D')


def apply_manual():
    from temba.orgs.models import Org
    from temba.flows.models import Flow
    populate_flow_launch_status(Org, Flow)


def apply_as_migration(apps, schema_editor):
    Flow = apps.get_model('flows', 'Flow')
    Org = apps.get_model('orgs', 'org')
    populate_flow_launch_status(Org, Flow)


class Migration(migrations.Migration):

    dependencies = [
        ('flows', '0138_auto_20190403_1417'),
    ]

    operations = [
        migrations.RunPython(apply_as_migration)
    ]
