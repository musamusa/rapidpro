from __future__ import absolute_import, unicode_literals

from django.contrib.auth import authenticate, login
from django.http import HttpResponse, JsonResponse
from temba.api.models import APIToken, api_token
from temba.api.v2.views import AuthenticateView as AuthenticateEndpointV2, BaseAPIView, ListAPIMixin
from temba.orgs.models import get_user_orgs


class AuthenticateView(AuthenticateEndpointV2):

    def form_valid(self, form, *args, **kwargs):
        username = form.cleaned_data.get('username')
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


class UserOrgsEndpoint(BaseAPIView, ListAPIMixin):
    """
    Provides the user's organizations and API tokens to use on Surveyor App
    """

    permission = 'orgs.org_api'

    def list(self, request, *args, **kwargs):
        user = request.user
        user_orgs = get_user_orgs(user)
        orgs = []

        role = APIToken.get_role_from_code('S')

        if role:
            for org in user_orgs:
                token = APIToken.get_or_create(org, user, role)
                orgs.append({'org': {'id': org.pk, 'name': org.name}, 'token': token.key})

        else:  # pragma: needs cover
            return HttpResponse(status=403)

        return JsonResponse({'orgs': orgs})
