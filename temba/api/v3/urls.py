from __future__ import absolute_import, unicode_literals

from django.conf.urls import url
from django.views.generic.base import RedirectView
from rest_framework.urlpatterns import format_suffix_patterns

from .views import AuthenticateView, UserOrgsEndpoint


urlpatterns = [
    # this HTML view redirects to its v2 equivalent
    url(r'^explorer/$', RedirectView.as_view(pattern_name='api.v2.explorer', permanent=True)),

    # these endpoints are retained for Android Surveyor clients
    url(r'^$', RedirectView.as_view(pattern_name='api.v2.explorer', permanent=True)),
    url(r'^authenticate/?$', AuthenticateView.as_view(), name='api.v3.authenticate'),
    url(r'^user/orgs/?$', UserOrgsEndpoint.as_view(), name='api.v3.user_orgs'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'api'])
