from __future__ import absolute_import, unicode_literals

from django.conf.urls import url
from django.views.generic.base import RedirectView
from rest_framework.urlpatterns import format_suffix_patterns

from .views import AuthenticateEndpoint


urlpatterns = [
    # this HTML view redirects to its v2 equivalent
    url(r'^explorer/$', RedirectView.as_view(pattern_name='api.v2.explorer', permanent=True)),

    # these endpoints are retained for Android Surveyor clients
    url(r'^$', RedirectView.as_view(pattern_name='api.v2.explorer', permanent=True)),
    url(r'^authenticate$', AuthenticateEndpoint.as_view(), name='api.v3.authenticate'),
    # url(r'^boundaries$', BoundaryEndpoint.as_view(), name='api.v1.boundaries'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json'])
