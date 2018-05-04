from __future__ import unicode_literals

from celery.task import task
from temba.utils.queues import nonoverlapping_task
from .models import ExportContactsTask, ContactGroupCount


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
