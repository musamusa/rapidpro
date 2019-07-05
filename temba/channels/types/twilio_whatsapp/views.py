from __future__ import unicode_literals, absolute_import

import phonenumbers

from uuid import uuid4

from django import forms
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from smartmin.views import SmartFormView

from temba.orgs.models import ACCOUNT_SID, ACCOUNT_TOKEN
from ...models import Channel
from ...views import ClaimViewMixin

from twilio import TwilioRestException


class ClaimView(ClaimViewMixin, SmartFormView):
    class Form(ClaimViewMixin.Form):
        phone_number = forms.CharField(label=_("WhatsApp number"),
                                       help_text=_("Type the WhatsApp number"))

        def clean_phone_number(self):
            org = self.request.user.get_org()
            phone_number = self.cleaned_data['phone_number']

            try:
                phone = phonenumbers.parse(phone_number)
                phone_number = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)
            except Exception:
                raise ValidationError(_('Invalid number. Ensure number includes country code, e.g. +14153019999'))

            # does a bot already exist on this account with that auth token
            existing = Channel.objects.filter(org=org, is_active=True, address=phone_number,
                                              channel_type='TWP').first()
            if existing:
                raise ValidationError(_("A WhatsApp channel for this phone number already exists on your account."))

            try:
                client = org.get_twilio_client()
                twilio_phones = client.phone_numbers.list(phone_number=phone_number)
                if not twilio_phones:
                    raise ValidationError(_("Phone number not found in your Twilio account"))
            except Exception as e:
                raise ValidationError(e.message)

            return phone_number

    form_class = Form

    def __init__(self, channel_type):
        super(ClaimView, self).__init__(channel_type)
        self.account = None
        self.client = None

    def pre_process(self, *args, **kwargs):
        org = self.request.user.get_org()
        try:
            self.client = org.get_twilio_client()
            if not self.client:
                return HttpResponseRedirect('%s?next=%s' % (reverse('orgs.org_twilio_connect'), reverse('channels.claim_twilio_whatsapp')))
            self.account = self.client.accounts.get(org.config_json()[ACCOUNT_SID])
        except TwilioRestException:
            return HttpResponseRedirect(reverse('orgs.org_twilio_connect'))

    def form_valid(self, form):
        org = self.request.user.get_org()
        phone_number = self.form.cleaned_data['phone_number']

        org_config = org.config_json()
        channel_uuid = uuid4()

        callback_domain = org.get_brand_domain()

        config = {Channel.CONFIG_ACCOUNT_SID: org_config[ACCOUNT_SID],
                  Channel.CONFIG_AUTH_TOKEN: org_config[ACCOUNT_TOKEN],
                  Channel.CONFIG_CALLBACK_DOMAIN: callback_domain}

        phone = phonenumbers.format_number(phonenumbers.parse(phone_number, None),
                                           phonenumbers.PhoneNumberFormat.NATIONAL)

        self.object = Channel.create(org, self.request.user, None, 'TWP', name=phone, address=phone_number,
                                     config=config, uuid=channel_uuid)

        return super(ClaimView, self).form_valid(form)
