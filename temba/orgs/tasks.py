from __future__ import absolute_import, print_function, unicode_literals

import time
import requests

from celery.task import task
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from temba.utils.queues import nonoverlapping_task
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
