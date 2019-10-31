from __future__ import unicode_literals, absolute_import

import requests
import time
import json
import six

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from temba.contacts.models import WS_SCHEME
from temba.msgs.models import WIRED
from temba.utils.http import HttpEvent
from .views import ClaimView
from ...models import Channel, ChannelType, SendException
from ...views import UpdateWsForm


class WsType(ChannelType):
    """
    A Websocket channel
    """
    code = 'WS'
    category = ChannelType.Category.API

    name = _("WebSocket Server")
    icon = 'icon-cord'
    show_config_page = False
    show_edit_page = True

    update_form = UpdateWsForm

    claim_blurb = _("Use our pluggable API to connect a website that you already have, and start surveys from there.")
    claim_view = ClaimView

    schemes = [WS_SCHEME]
    max_length = 1600
    attachment_support = True

    def send(self, channel, msg, text):
        data = {
            'id': str(msg.id),
            'text': text,
            'to': msg.urn_path,
            'to_no_plus': msg.urn_path.lstrip('+'),
            'from': channel.address,
            'from_no_plus': channel.address.lstrip('+'),
            'channel': str(channel.id)
        }
        start = time.time()

        headers = {
            'Content-Type': 'application/json',
            'User-agent': 'CCL'
        }

        if hasattr(msg, 'metadata'):
            data['metadata'] = msg.metadata

        if hasattr(msg, 'attachments') and msg.attachments:
            data['attachments'] = msg.attachments

        payload = json.dumps(data)
        event = HttpEvent('POST', settings.WS_URL, payload)

        try:
            response = requests.post(settings.WS_URL, data=payload, headers=headers, timeout=5)
            event.status_code = response.status_code
            event.response_body = response.text

        except Exception as e:
            raise SendException(six.text_type(e), event=event, start=start)

        if response.status_code != 200 and response.status_code != 201 and response.status_code != 202:
            raise SendException("Got non-200 response [%d] from WebSocket Server" % response.status_code,
                                event=event, start=start)

        Channel.success(channel, msg, WIRED, start, event=event)
