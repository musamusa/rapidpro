from __future__ import absolute_import, unicode_literals

from django.contrib.auth import authenticate, login
from django.http import HttpResponse, JsonResponse
from temba.api.models import APIToken, api_token
from temba.api.v1.views import AuthenticateEndpoint as AuthenticateEndpointV1


class AuthenticateEndpoint(AuthenticateEndpointV1):

    def form_valid(self, form, *args, **kwargs):
        username = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        role_code = form.cleaned_data.get('role')

        user = authenticate(username=username, password=password)
        if user and user.is_active:
            login(self.request, user)

            role = APIToken.get_role_from_code(role_code)

            if role:
                token = api_token(user)
                return JsonResponse(dict(token=token), safe=False)
            else:  # pragma: needs cover
                return HttpResponse(status=403)
        else:  # pragma: needs cover
            return HttpResponse(status=403)
