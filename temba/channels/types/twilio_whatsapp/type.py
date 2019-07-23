from __future__ import unicode_literals, absolute_import

import time
import six

from django.utils.translation import ugettext_lazy as _

from twilio import TwilioRestException

from temba.contacts.models import TWILIO_WHATSAPP_SCHEME
from temba.channels.views import TWILIO_SUPPORTED_COUNTRIES_CONFIG
from temba.msgs.models import Attachment, WIRED
from temba.utils.timezones import timezone_to_country_code
from temba.utils.twilio import TembaTwilioRestClient
from .views import ClaimView
from ...models import Channel, ChannelType, SendException


class TwilioWhatsappType(ChannelType):
    """
    A Twilio WhatsApp channel
    """
    code = 'TWP'
    category = ChannelType.Category.SOCIAL_MEDIA

    name = "Twilio WhatsApp"
    icon = 'icon-whatsapp'
    show_config_page = True

    claim_blurb = _("""Add a WhatsApp number from Twilio to send and receive messages from WhatsApp users.""")
    claim_view = ClaimView

    schemes = [TWILIO_WHATSAPP_SCHEME]
    max_length = 1600
    attachment_support = True

    def is_recommended_to(self, user):
        org = user.get_org()
        countrycode = timezone_to_country_code(org.timezone)
        return countrycode in TWILIO_SUPPORTED_COUNTRIES_CONFIG

    def send(self, channel, msg, text):
        callback_url = Channel.build_twilio_callback_url(channel.callback_domain, channel.channel_type, channel.uuid,
                                                         msg.id)

        start = time.time()
        media_urls = []

        if msg.attachments:
            # for now we only support sending one attachment per message but this could change in future
            attachment = Attachment.parse_all(msg.attachments)[0]
            media_urls = [attachment.url]

        config = channel.config
        client = TembaTwilioRestClient(config.get(Channel.CONFIG_ACCOUNT_SID),
                                       config.get(Channel.CONFIG_AUTH_TOKEN))

        try:
            client.messages.create(to='whatsapp:%s' % msg.urn_path,
                                   from_='whatsapp:%s' % channel.address,
                                   body=text,
                                   media_url=media_urls,
                                   status_callback=callback_url)

            Channel.success(channel, msg, WIRED, start, events=client.messages.events)

        except TwilioRestException as e:
            fatal = False

            # user has blacklisted us, stop the contact
            if e.code == 21610:
                from temba.contacts.models import Contact
                fatal = True
                contact = Contact.objects.get(id=msg.contact)
                contact.stop(contact.modified_by)

            raise SendException(e.msg, events=client.messages.events, fatal=fatal)

        except Exception as e:
            raise SendException(six.text_type(e), events=client.messages.events)
