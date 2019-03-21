from __future__ import absolute_import, print_function, unicode_literals

import time
import requests
import json
import pytz

from celery.task import task
from parse_rest.connection import register
from parse_rest.datatypes import Object
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.template.defaultfilters import slugify
from temba.utils import str_to_datetime
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


@task(track_started=True, name='refresh_salesforce_access_tokens')
def refresh_salesforce_access_tokens():  # pragma: needs cover

    for org in Org.objects.all().order_by('pk'):
        (sf_instance_url, sf_access_token, sf_refresh_token) = org.get_salesforce_credentials()

        if not org.is_suspended() and sf_instance_url and sf_refresh_token:
            print('> Updating Salesforce access token for org %s' % org.slug)

            data = {
                'grant_type': 'refresh_token',
                'refresh_token': sf_refresh_token,
                'client_id': settings.SALESFORCE_CONSUMER_KEY,
                'client_secret': settings.SALESFORCE_CONSUMER_SECRET
            }
            headers = {'content-type': 'application/x-www-form-urlencoded'}
            headers.update(settings.OUTGOING_REQUEST_HEADERS)
            response = requests.post(settings.SALESFORCE_ACCESS_TOKEN_URL, data=data, headers=headers)

            if response.status_code == 200:
                response = response.json()
                org.connect_salesforce_account(sf_instance_url, response.get('access_token'), sf_refresh_token, org.created_by)


@task(track_started=True, name='import_data_to_parse')
def import_data_to_parse(branding, user_email, iterator, parse_url, parse_headers, collection, collection_type, collection_real_name, filename, needed_create_header, tz, dayfirst):  # pragma: needs cover
    start = time.time()
    load_len = len(iterator) - 1

    print("Started task to import %s row(s) to Parse" % str(load_len))

    parse_batch_url = '%s/batch' % settings.PARSE_URL
    register(settings.PARSE_APP_ID, settings.PARSE_REST_KEY, master=settings.PARSE_MASTER_KEY)

    tz = pytz.timezone(tz)

    new_fields = {}
    fields_map = {}

    failures = []
    success = 0

    batch_size = 1000
    batch_package = []
    batch_counter = 0
    order = 1

    for i, row in enumerate(iterator):
        if i == 0:
            counter = 0
            for item in row:
                if str(item).startswith('numeric_'):
                    field_type = 'Number'
                    item = item.replace('numeric_', '')
                elif str(item).startswith('date_'):
                    field_type = 'Date'
                    item = item.replace('date_', '')
                else:
                    field_type = 'String'

                new_key = str(slugify(item)).replace('-', '_')
                new_fields[new_key] = dict(type=field_type)

                fields_map[counter] = dict(name=new_key, type=field_type)
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
                    field_value = row[item]

                    if fields_map[item].get('type') == 'Number':
                        field_value = float(field_value)
                    elif fields_map[item].get('type') == 'Date':
                        field_value = field_value.replace('-', '/')
                        try:
                            field_value = str_to_datetime(date_str=field_value, tz=tz, dayfirst=dayfirst, fill_time=False)
                        except Exception:
                            field_value = None
                    else:
                        field_value = str(field_value) if field_value.__class__.__name__ == 'int' \
                            else field_value.encode('utf-8', errors='ignore').strip()

                    payload[fields_map[item].get('name')] = field_value
                except Exception:
                    if str(i) not in failures:
                        failures.append(str(i))

            payload['order'] = order
            real_collection = Object.factory(collection)
            new_item = real_collection(**payload)
            batch_package.append(new_item)
            batch_counter += 1
            order += 1

        if batch_counter >= batch_size:
            methods = list([m.save for m in batch_package])
            if not methods:
                return
            queries, callbacks = list(zip(*[m(batch=True) for m in methods]))
            response = requests.post(parse_batch_url, data=json.dumps(dict(requests=queries)), headers=parse_headers)
            if response.status_code == 200:
                for item in response.json():
                    if "success" in item:
                        success += 1
                    else:
                        failures.append(item.get('error'))
            batch_package = []
            batch_counter = 0

    # commit any remaining objects
    if batch_package:
        methods = list([m.save for m in batch_package])
        if not methods:
            return
        queries, callbacks = list(zip(*[m(batch=True) for m in methods]))
        response = requests.post(parse_batch_url, data=json.dumps(dict(requests=queries)), headers=parse_headers)
        if response.status_code == 200:
            for item in response.json():
                if "success" in item:
                    success += 1
                else:
                    failures.append(item.get('error'))

    print(" -- Importation task ran in %0.2f seconds" % (time.time() - start))

    subject = _("Your %s Upload to Community Connect is Complete") % collection_type
    template = "orgs/email/importation_email"

    failures = ', '.join(failures) if failures else None

    context = dict(now=timezone.now(), subject=subject, success=success, failures=failures, collection_real_name=collection_real_name, collection_type=collection_type, filename=filename)

    send_template_email(user_email, subject, template, context, branding)
