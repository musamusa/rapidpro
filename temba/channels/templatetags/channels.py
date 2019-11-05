from __future__ import unicode_literals

from django import template

register = template.Library()


@register.filter
def channel_icon(channel):
    return channel.get_type().icon


@register.filter
def adapt_for_widget(text):
    return text.replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
