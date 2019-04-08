from __future__ import unicode_literals, absolute_import

import requests

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from smartmin.views import SmartFormView
from ...models import Channel
from ...views import ClaimViewMixin


class ClaimView(ClaimViewMixin, SmartFormView):
    class Form(ClaimViewMixin.Form):
        url = forms.CharField(label=_('WebSocket URL'))

        def clean_url(self):
            org = self.request.user.get_org()
            value = self.cleaned_data['url']

            # does a ws channel already exists on this account with that url
            for channel in Channel.objects.filter(org=org, is_active=True, channel_type=self.channel_type.code):
                if channel.config_json()['url'] == value:
                    raise ValidationError(_("A WebSocket channel for this URL already exists on your account."))

            try:
                requests.get(value)
            except Exception as e:
                raise ValidationError(e.message)

            return value

    form_class = Form

    def form_valid(self, form):
        org = self.request.user.get_org()
        cleaned_data = form.cleaned_data

        data = {Channel.CONFIG_WS_URL: cleaned_data.get('url')}

        self.object = Channel.create(org, self.request.user, None, self.channel_type,
                                     name='WebSocket Server', address=cleaned_data.get('url'), config=data)

        return super(ClaimView, self).form_valid(form)
