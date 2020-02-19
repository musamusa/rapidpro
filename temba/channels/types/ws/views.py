from __future__ import unicode_literals, absolute_import

import requests
import regex

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

        address = forms.URLField(label=_('WebSocket Address'), max_length=255, initial=settings.WS_URL)

        def clean_channel_name(self):
            org = self.request.user.get_org()
            value = self.cleaned_data['channel_name']

            if not regex.match(r'^[A-Za-z0-9_.\-*() ]+$', value, regex.V0):
                raise forms.ValidationError('Please make sure the websocket name only contains '
                                            'alphanumeric characters [0-9a-zA-Z], hyphens, and underscores')

            # does a ws channel already exists on this account with that name
            existing = Channel.objects.filter(org=org, is_active=True, channel_type=self.channel_type.code,
                                              name=value).first()

            if existing:
                raise ValidationError(_("A WebSocket channel for this name already exists on your account."))

            try:
                requests.get(settings.WS_URL)
            except Exception as e:
                raise ValidationError(e.message)

            return value

        def clean_address(self):
            address = self.cleaned_data['address']

            try:
                requests.get(address)
            except Exception as e:
                raise ValidationError(e.message)

            return address

    form_class = Form
    exclude = [] if settings.WS_ALLOW_CHANGE_ADDRESS else ['address']

    def form_valid(self, form):
        org = self.request.user.get_org()
        cleaned_data = form.cleaned_data

        channel_name = cleaned_data.get('channel_name')
        address = cleaned_data.get('address', settings.WS_URL)

        branding = org.get_branding()

        basic_config = {
            'welcome_message': '',
            'title': '%s %s' % (settings.WIDGET_THEMES[0]['title'], channel_name),
            'theme': settings.WIDGET_THEMES[0]['name'],
            'logo': 'https://%s%s%s' % (settings.HOSTNAME, settings.STATIC_URL, branding.get('favico')),
            'chat_header_bg_color': settings.WIDGET_THEMES[0]['header_bg'],
            'chat_header_text_color': settings.WIDGET_THEMES[0]['header_txt'],
            'automated_chat_bg': settings.WIDGET_THEMES[0]['automated_chat_bg'],
            'automated_chat_txt': settings.WIDGET_THEMES[0]['automated_chat_txt'],
            'user_chat_bg': settings.WIDGET_THEMES[0]['user_chat_bg'],
            'user_chat_txt': settings.WIDGET_THEMES[0]['user_chat_txt'],
            'widget_bg_color': settings.WIDGET_THEMES[0]['widget_bg'],
            'logo_style': settings.WIDGET_THEMES[0]['logo_style'],
            'chat_button_height': settings.WIDGET_THEMES[0]['chat_button_height'],
            'side_padding': settings.WIDGET_THEMES[0]['side_padding'],
            'bottom_padding': settings.WIDGET_THEMES[0]['bottom_padding'],
            'side_of_screen': settings.WIDGET_THEMES[0]['side_of_screen']
        }

        self.object = Channel.create(org, self.request.user, None, self.channel_type, name=channel_name,
                                     address=address, config=basic_config)

        return super(ClaimView, self).form_valid(form)
