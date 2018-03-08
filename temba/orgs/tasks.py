from __future__ import absolute_import, print_function, unicode_literals

import time
import requests
import json

from celery.task import task
from parse_rest.connection import register
from parse_rest.datatypes import Object
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.template.defaultfilters import slugify
from temba.utils.queues import nonoverlapping_task
from temba.utils.email import send_template_email
from .models import CreditAlert, Invitation, Org, TopUpCredits


@task(track_started=True, name='send_invitation_email_task')
def send_invitation_email_task(invitation_id):
    invitation = Invitation.objects.get(pk=invitation_id)
    invitation.send_email()


@task(track_started=True, name='send_alert_email_task')
def send_alert_email_task(alert_id):
    alert = CreditAlert.objects.get(pk=alert_id)
    alert.send_email()


@task(track_started=True, name='check_credits_task')
def check_credits_task():  # pragma: needs cover
    CreditAlert.check_org_credits()


@task(track_started=True, name='calculate_credit_caches')
def calculate_credit_caches():  # pragma: needs cover
    """
    Repopulates the active topup and total credits for each organization
    that received messages in the past week.
    """
    # get all orgs that have sent a message in the past week
    last_week = timezone.now() - timedelta(days=7)

    # for every org that has sent a message in the past week
    for org in Org.objects.filter(msgs__created_on__gte=last_week).distinct('pk'):
        start = time.time()
        org._calculate_credit_caches()
        print(" -- recalculated credits for %s in %0.2f seconds" % (org.name, time.time() - start))


@nonoverlapping_task(track_started=True, name="squash_topupcredits", lock_key='squash_topupcredits')
def squash_topupcredits():
    TopUpCredits.squash()


@task(track_started=True, name='import_data_to_parse')
def import_data_to_parse(branding, user_email, iterator, parse_url, parse_headers, collection, collection_type, filename, needed_create_header):  # pragma: needs cover
    start = time.time()
    print("Started task to import %s row(s) to Parse" % str(len(iterator) - 1))

    register(settings.PARSE_APP_ID, settings.PARSE_REST_KEY, master=settings.PARSE_MASTER_KEY)

    new_fields = {}
    fields_map = {}

    failures = []
    success = 0

    for i, row in enumerate(iterator):
        if i == 0:
            counter = 0
            for item in row:
                new_key = str(slugify(item)).replace('-', '_')
                new_fields[new_key] = dict(type='String')

                fields_map[counter] = new_key
                counter += 1

            if needed_create_header:
                add_new_fields = {
                    "className": collection,
                    "fields": new_fields
                }
                requests.put(parse_url, data=json.dumps(add_new_fields), headers=parse_headers)
        else:
            payload = dict()
            for item in fields_map.keys():
                try:
                    payload[fields_map[item]] = row[item].replace('"', '')
                except Exception:
                    failures.append(str(i))

            real_collection = Object.factory(collection)
            new_item = real_collection(**payload)
            new_item.save()
            success += 1

    print(" -- Importation task ran in %0.2f seconds" % (time.time() - start))

    subject = _("Your %s Upload to Community Connect is Complete") % collection_type
    template = "orgs/email/importation_email"

    failures = ', '.join(failures) if failures else None

    context = dict(now=timezone.now(), subject=subject, success=success, failures=failures, collection=collection, collection_type=collection_type, filename=filename)

    send_template_email(user_email, subject, template, context, branding)
