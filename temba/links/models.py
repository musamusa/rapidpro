# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import six
from django.db import models
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from temba.orgs.models import Org
from temba.utils.models import TembaModel


@six.python_2_unicode_compatible
class TrackableLink(TembaModel):

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

    @classmethod
    def create(cls, org, user, name, destination):
        shorten_url = 'test'
        flow = TrackableLink.objects.create(org=org, name=name, slug=slugify(name), shorten_url=shorten_url,
                                            destination=destination, created_by=user, modified_by=user)
        return flow

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('-created_on',)
