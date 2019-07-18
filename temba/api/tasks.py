from __future__ import print_function, unicode_literals

import requests
import json

from celery.task import task
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_redis import get_redis_connection
from django.template import loader
from django.core.mail import send_mail

from temba.utils import chunk_list
from temba.utils.queues import nonoverlapping_task
from temba.utils.email import send_template_email
from .models import WebHookEvent, WebHookResult

from oauth2client.service_account import ServiceAccountCredentials


@task(track_started=True, name='deliver_event_task')
def deliver_event_task(event_id):  # pragma: no cover
    # get a lock
    r = get_redis_connection()

    # try to acquire a lock, at most it will last 1 min
    key = 'deliver_event_%d' % event_id

    if not r.get(key):
        with r.lock(key, timeout=60):
            # load our event and try to deliver it
            event = WebHookEvent.objects.get(pk=event_id)

            if event.status != WebHookEvent.STATUS_COMPLETE and event.status != WebHookEvent.STATUS_FAILED:
                result = event.deliver()

                # record our result.  We do this here and not in deliver() because we want to allow
                # testing of web hooks in the UI without having to actually create any model objects
                WebHookResult.record_result(event, result)


@task(track_started=True, name='retry_events_task')
def retry_events_task():  # pragma: no cover
    print("** retrying errored webhook events")

    # get all events that have an error and need to be retried
    now = timezone.now()
    for event in WebHookEvent.objects.filter(status=WebHookEvent.STATUS_ERRORED, next_attempt__lte=now).exclude(event=WebHookEvent.TYPE_FLOW):
        deliver_event_task.delay(event.pk)

    # also get those over five minutes old that are still pending
    five_minutes_ago = now - timedelta(minutes=5)
    for event in WebHookEvent.objects.filter(status=WebHookEvent.STATUS_PENDING, created_on__lte=five_minutes_ago).exclude(event=WebHookEvent.TYPE_FLOW):
        deliver_event_task.delay(event.pk)

    # and any that were errored and haven't been retried for some reason
    fifteen_minutes_ago = now - timedelta(minutes=15)
    for event in WebHookEvent.objects.filter(status=WebHookEvent.STATUS_ERRORED, modified_on__lte=fifteen_minutes_ago).exclude(event=WebHookEvent.TYPE_FLOW):
        deliver_event_task.delay(event.pk)


@nonoverlapping_task(track_started=True, name='trim_webhook_event_task')
def trim_webhook_event_task():
    """
    Runs daily and clears any webhoook events older than settings.SUCCESS_LOGS_TRIM_TIME(default: 48) hours.
    """

    # keep success messages for only SUCCESS_LOGS_TRIM_TIME hours
    success_logs_trim_time = settings.SUCCESS_LOGS_TRIM_TIME

    # keep errors for ALL_LOGS_TRIM_TIME days
    all_logs_trim_time = settings.ALL_LOGS_TRIM_TIME

    if success_logs_trim_time:
        success_log_later = timezone.now() - timedelta(hours=success_logs_trim_time)
        event_ids = WebHookEvent.objects.filter(created_on__lte=success_log_later, status=WebHookEvent.STATUS_COMPLETE)
        event_ids = event_ids.values_list('id', flat=True)
        for batch in chunk_list(event_ids, 1000):
            WebHookEvent.objects.filter(id__in=batch).delete()

    if all_logs_trim_time:
        all_log_later = timezone.now() - timedelta(hours=all_logs_trim_time)
        event_ids = WebHookEvent.objects.filter(created_on__lte=all_log_later)
        event_ids = event_ids.values_list('id', flat=True)
        for batch in chunk_list(event_ids, 1000):
            WebHookEvent.objects.filter(id__in=batch).delete()


@task(track_started=True, name='send_account_manage_email_task')
def send_account_manage_email_task(user_email, message):
    branding = settings.BRANDING.get(settings.DEFAULT_BRAND)

    if not user_email or not branding:  # pragma: needs cover
        return

    subject = _("%(name)s Request Info") % branding
    template = "orgs/email/manage_account_email"

    context = dict(message=message)
    context['subject'] = subject

    send_template_email(user_email, subject, template, context, branding)


@task(track_started=True, name='send_recovery_mail')
def send_recovery_mail(context, emails):
    hostname = getattr(settings, 'HOSTNAME')

    col_index = hostname.find(':')
    domain = hostname[:col_index] if col_index > 0 else hostname

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'website@%s' % domain)
    user_email_template = getattr(settings, "USER_FORGET_EMAIL_TEMPLATE", "smartmin/users/user_email.txt")

    email_template = loader.get_template(user_email_template)
    send_mail(_('Password Changing Request'), email_template.render(context), from_email, emails, fail_silently=False)


@task(track_started=True, name='push_notification_to_fcm')
def push_notification_to_fcm(user_tokens):
    scopes = ['https://www.googleapis.com/auth/firebase.messaging']
    credentials = ServiceAccountCredentials._from_parsed_json_keyfile(settings.FCM_CONFIG, scopes)
    access_token_info = credentials.get_access_token()

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer %s' % access_token_info.access_token
    }

    for token in user_tokens:
        data = {
            "message": {
                "token": token,
                "notification": {
                    "body": str(_("There is a new access request. Check your User Approval session")),
                    "title": str(_("Surveyor User Request"))
                }
            }
        }

        try:
            print("[%s] Sending push notification..." % timezone.now())
            response = requests.post(settings.FCM_HOST, data=json.dumps(data), headers=headers, timeout=5)
            if response.status_code == 200:
                print("[%s] Push notification sent successfully" % timezone.now())
        except Exception as e:  # pragma: no cover
            import traceback
            traceback.print_exc(e)
