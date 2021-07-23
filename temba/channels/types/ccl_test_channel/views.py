from smartmin.views import SmartFormView

from django import forms
from django.utils.translation import ugettext_lazy as _

from temba.utils.fields import SelectWidget

from ...models import Channel
from ...views import ClaimViewMixin, ALL_COUNTRIES


class ClaimView(ClaimViewMixin, SmartFormView):
    class Form(ClaimViewMixin.Form):
        shortcode = forms.CharField(max_length=6, min_length=1, help_text=_("Your short code on CCL Test Channel"))
        username = forms.CharField(max_length=32, help_text=_("Your username on CCL Test Channel"))
        api_key = forms.CharField(max_length=64, help_text=_("Your api key, should be 64 characters"))
        country = forms.ChoiceField(
            choices=ALL_COUNTRIES,
            label=_("Country"),
            required=False,
            widget=SelectWidget(attrs={"searchable": True}),
            help_text=_("The country this phone number is used in"),
        )

    form_class = Form

    def form_valid(self, form):
        user = self.request.user
        org = user.get_org()

        data = form.cleaned_data

        config = dict(username=data["username"], api_key=data["api_key"])

        self.object = Channel.create(
            org,
            user,
            data["country"],
            self.channel_type,
            name="CCL : %s" % data["shortcode"],
            address=data["shortcode"],
            config=config,
        )

        return super().form_valid(form)
