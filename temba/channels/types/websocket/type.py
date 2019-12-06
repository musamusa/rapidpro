from django.utils.translation import ugettext_lazy as _
from temba.contacts.models import WEBSOCKET_SCHEME
from .views import ClaimView
from ...models import ChannelType
from ...views import UpdateWebSocketForm


class WebSocketType(ChannelType):
    """
    A WebSocket channel
    """

    code = "WS"
    category = ChannelType.Category.API

    courier_url = r"^ws/(?P<uuid>[a-z0-9\-]+)/receive$"

    name = _("WebSocket Channel")
    icon = "icon-cord"
    show_config_page = True
    show_edit_page = True

    update_form = UpdateWebSocketForm

    claim_blurb = _("Use our pluggable API to connect a website that you already have, and start surveys from there.")
    claim_view = ClaimView

    schemes = [WEBSOCKET_SCHEME]
    max_length = 2000
    attachment_support = True

    async_activation = False
    quick_reply_text_size = 50
