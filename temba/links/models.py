# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import six

from django.db import models
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from temba.contacts.models import Contact
from temba.orgs.models import Org
from temba.utils.models import TembaModel


class LinkException(Exception):
    def __init__(self, *args, **kwargs):
        super(LinkException, self).__init__(*args, **kwargs)


@six.python_2_unicode_compatible
class Link(TembaModel):

    name = models.CharField(max_length=64,
                            help_text=_("The name for this trackable link"))

    slug = models.SlugField(max_length=64,
                            help_text="The trackable link slug")

    shorten_url = models.URLField(max_length=100,
                                  help_text="The trackable link slug")

    destination = models.URLField(max_length=255,
                                  help_text="The destination URL for this trackable link")

    org = models.ForeignKey(Org, related_name='links')

    is_archived = models.BooleanField(default=False,
                                      help_text=_("Whether this trackable link is archived"))

    clicks_count = models.PositiveIntegerField(default=0,
                                               help_text="Clicks count for this trackable link")

    contacts = models.ManyToManyField(Contact, related_name="contact_links",
                                      help_text=_("The users which clicked on this link"))

    @classmethod
    def create(cls, org, user, name, destination, shorten_url):
        flow = Link.objects.create(org=org, name=name, slug=slugify(name), shorten_url=shorten_url,
                                   destination=destination, created_by=user, modified_by=user)
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

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('-created_on',)
