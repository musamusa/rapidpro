from django.utils.translation import ugettext_lazy as _

from temba.contacts.models import URN

from ...models import ChannelType
from .views import ClaimView


class CCLTestChannel(ChannelType):
    """
    A CCL Test channel
    """

    code = "CCL"
    category = ChannelType.Category.PHONE

    courier_url = r"^ccl/(?P<uuid>[a-z0-9\-]+)/(?P<action>receive|status)$"

    name = "CCL Test Channel"
    icon = "icon-channel-external"

    claim_blurb = _("You can purchase a short code from %(link)s and connect it in a few simple steps.") % {
        "link": """<a href="http://communityconnectlabs.com">CCL Test Channel</a>"""
    }
    claim_view = ClaimView

    schemes = [URN.TEL_SCHEME]
    max_length = 160
    attachment_support = False

    configuration_blurb = _(
        "To finish configuring your CCL Test Channel connection you'll need to set the following callback URLs on the "
        "CCL Test Channel website under your account."
    )

    configuration_urls = (
        dict(
            label=_("Callback URL"),
            url="https://{{ channel.callback_domain }}{% url 'courier.ccl' channel.uuid 'receive' %}",
            description=_(
                "Use this url to send message"
            ),
        ),
        dict(
            label=_("Delivery URL"),
            url="https://{{ channel.callback_domain }}{% url 'courier.ccl' channel.uuid 'status' %}",
            description=_(
                "this url is to request message status",
            ),
        ),
    )
