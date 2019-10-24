from __future__ import unicode_literals, absolute_import

import requests

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from smartmin.views import SmartFormView
from ...models import Channel
from ...views import ClaimViewMixin


class ClaimView(ClaimViewMixin, SmartFormView):
    class Form(ClaimViewMixin.Form):
        channel_name = forms.CharField(label=_('WebSocket Name'), max_length=64)

        def clean_channel_name(self):
            org = self.request.user.get_org()
            value = self.cleaned_data['channel_name']

            # does a ws channel already exists on this account with that url
            for channel in Channel.objects.filter(org=org, is_active=True, channel_type=self.channel_type.code):
                if channel.name == value:
                    raise ValidationError(_("A WebSocket channel for this name already exists on your account."))

            try:
                requests.get(settings.WS_URL)
            except Exception as e:
                raise ValidationError(e.message)

            return value

    form_class = Form

    def form_valid(self, form):
        org = self.request.user.get_org()
        cleaned_data = form.cleaned_data

        self.object = Channel.create(org, self.request.user, None, self.channel_type,
                                     name=cleaned_data.get('channel_name'), address=settings.WS_URL, config={})

        return super(ClaimView, self).form_valid(form)
