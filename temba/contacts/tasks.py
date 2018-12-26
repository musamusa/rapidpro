from __future__ import unicode_literals

from celery.task import task
from temba.utils.queues import nonoverlapping_task
from .models import ExportContactsTask, ContactGroupCount, Contact


@task(track_started=True, name='export_contacts_task')
def export_contacts_task(id):
    """
    Export contacts to a file and e-mail a link to the user
    """
    ExportContactsTask.objects.get(id=id).perform()


@task(track_started=True, name='export_salesforce_contacts_task')
def export_salesforce_contacts_task(id):
    """
    Export contacts to Salesforce and sends an e-mail to the user when it gets the end.
    """
    ExportContactsTask.objects.get(id=id).perform(event='salesforce')


@nonoverlapping_task(track_started=True, name='squash_contactgroupcounts')
def squash_contactgroupcounts():
    """
    Squashes our ContactGroupCounts into single rows per ContactGroup
    """
    ContactGroupCount.squash()


@task(track_started=True, name='import_salesforce_contacts_task')
def import_salesforce_contacts_task(sf_instance_url, sf_access_token, sf_query, fields, user_id, org_id, counter, contact_group_name):
    """
    Import contacts from Salesforce and sends an e-mail to the user when it gets the end.
    """
    Contact.import_from_salesforce(sf_instance_url, sf_access_token, sf_query, fields, user_id, org_id, counter, contact_group_name)


@task(track_started=True, name='unblock_contacts_task')
def unblock_contacts_task(contact_ids, org_id):
    """
    Unblock contacts
    """
    Contact.objects.filter(pk__in=contact_ids, org_id=org_id).update(is_blocked=False)
