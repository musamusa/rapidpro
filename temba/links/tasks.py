from __future__ import print_function, unicode_literals

import logging

from celery.task import task

from .models import Link, LinkContacts

logger = logging.getLogger(__name__)


@task(track_started=True, name='handle_link_task')
def handle_link_task(link_id, contact_id):
    link = Link.objects.filter(pk=link_id).only('created_by', 'modified_by').first()
    if link and contact_id not in [item.get('contact__id') for item in link.contacts.all().select_related().only('contact__id').values('contact__id')]:
        link_contact_args = dict(link=link,
                                 contact_id=contact_id,
                                 created_by=link.created_by,
                                 modified_by=link.modified_by)
        LinkContacts.objects.create(**link_contact_args)

        link.clicks_count += 1
        link.save(update_fields=['clicks_count'])
