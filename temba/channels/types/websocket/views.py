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

            return value

    form_class = Form

    def form_valid(self, form):
        org = self.request.user.get_org()
        cleaned_data = form.cleaned_data
        branding = org.get_branding()

        channel_name = cleaned_data.get("channel_name")
        default_theme = settings.WIDGET_THEMES.get(settings.WIDGET_DEFAULT_THEME, {})

        basic_config = {
            "welcome_message": "",
            "title": f"Chat with {channel_name}",
            "theme": settings.WIDGET_DEFAULT_THEME,
            'logo': f"https://{settings.HOSTNAME}{settings.STATIC_URL}{branding.get('favico')}",
            'chat_header_bg_color': default_theme.get("header_bg"),
            'chat_header_text_color': default_theme.get("header_txt"),
            'automated_chat_bg': default_theme.get("automated_chat_bg"),
            'automated_chat_txt': default_theme.get("automated_chat_txt"),
            'user_chat_bg': default_theme.get("user_chat_bg"),
            'user_chat_txt': default_theme.get("user_chat_txt"),
            'chat_timeout': 120
        }

        self.object = Channel.create(org, self.request.user, None, self.channel_type, name=channel_name,
                                     config=basic_config)

        return super().form_valid(form)
