# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def create_campaign_field(apps, schema_editor):
    from temba.contacts.models import ContactField
    from temba.values.models import Value
    from ..models import Org

    for org in Org.objects.filter(is_active=True).order_by('id'):
        if not org.contactfields.filter(key=settings.CAMPAIGN_FIELD):
            print('> Creating campaign field for org #%s' % org.pk)

            ContactField.objects.create(org=org, key=settings.CAMPAIGN_FIELD, created_by=org.created_by,
                                        modified_by=org.created_by, label=settings.CAMPAIGN_FIELD,
                                        show_in_table=False, value_type=Value.TYPE_DATETIME)


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0036_ensure_anon_user_exists'),
    ]

    operations = [
        migrations.RunPython(create_campaign_field)
    ]
