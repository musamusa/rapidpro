# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from temba.middleware import BrandingMiddleware
from temba.orgs.models import Org


def update_template_optin():
    orgs = Org.objects.all().order_by('id')

    for org in orgs:

        print('> Update template for org #%s' % org.id)

        branding = BrandingMiddleware.get_branding_for_host(org.brand)
        if not branding:
            branding = BrandingMiddleware.get_branding_for_host('')

        org.create_sample_flows(branding.get('api_link', ''))


def apply_as_migration(apps, schema_editor):
    update_template_optin()


def apply_manual():
    update_template_optin()


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0036_ensure_anon_user_exists'),
    ]

    operations = [
        migrations.RunPython(apply_as_migration)
    ]
