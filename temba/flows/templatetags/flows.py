import json

from django import template

register = template.Library()


@register.filter
def list_embedded_data(keyword):
    embedded_data = json.loads(keyword.embedded_data) if keyword.embedded_data else None
    embedded_data_list = [dict(field=item, value=embedded_data.get(item)) for item in sorted(embedded_data.keys())] \
        if embedded_data else []
    return embedded_data_list
