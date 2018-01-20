# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import six

from itertools import chain

from django.db import models
from django.utils.translation import ugettext_lazy as _

from smartmin.models import SmartModel

from temba.contacts.models import Contact
from temba.contacts.search import contact_search, SearchException
from temba.orgs.models import Org
from temba.utils.models import TembaModel


MAX_HISTORY = 50


class LinkException(Exception):
    def __init__(self, *args, **kwargs):
        super(LinkException, self).__init__(*args, **kwargs)


@six.python_2_unicode_compatible
class Link(TembaModel):

    name = models.CharField(max_length=64,
                            help_text=_("The name for this trackable link"))

    destination = models.URLField(max_length=255,
                                  help_text="The destination URL for this trackable link")

    org = models.ForeignKey(Org, related_name='links')

    is_archived = models.BooleanField(default=False,
                                      help_text=_("Whether this trackable link is archived"))

    clicks_count = models.PositiveIntegerField(default=0,
                                               help_text="Clicks count for this trackable link")

    @classmethod
    def create(cls, org, user, name, destination):
        flow = Link.objects.create(org=org, name=name, destination=destination, created_by=user, modified_by=user)
        return flow

    def get_contacts(self):
        return self.contacts.all().select_related().only('pk', 'name')

    @classmethod
    def apply_action_archive(cls, user, links):
        changed = []

        for link in links:
            link.archive()
            changed.append(link.pk)

        return changed

    @classmethod
    def apply_action_restore(cls, user, links):
        changed = []
        for link in links:
            try:
                link.restore()
                changed.append(link.pk)
            except LinkException:  # pragma: no cover
                pass
        return changed

    def archive(self):
        self.is_archived = True
        self.save(update_fields=['is_archived'])

    def restore(self):
        self.is_archived = False
        self.save(update_fields=['is_archived'])

    def get_activity(self, after, before, search):
        """
        Gets this link's activity of contacts in the given time window
        """

        contacts = LinkContacts.objects.filter(link=self, created_on__gte=after, created_on__lt=before)
        if search:
            try:
                real_contacts = Contact.objects.filter(id__in=contacts.values_list('contact__id')).only('id')
                search_contacts = contact_search(self.org, search, real_contacts, None)
                contacts = contacts.filter(contact__id__in=search_contacts.values_list('id'))
            except SearchException as e:
                self.search_error = six.text_type(e)
                contacts = Contact.objects.none()

        # wrap items, chain and sort by time
        activity = chain(
            [{'type': 'contact', 'time': c.created_on, 'obj': c} for c in contacts]
        )

        return sorted(activity, key=lambda i: i['time'], reverse=True)[:MAX_HISTORY]

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('-created_on',)


class LinkContacts(SmartModel):
    link = models.ForeignKey(Link, related_name="contacts")

    contact = models.ForeignKey(Contact, related_name="contact_links",
                                help_text=_("The users which clicked on this link"))

    def __str__(self):
        return "%s" % self.contact.get_display()
