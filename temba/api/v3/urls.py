from __future__ import absolute_import, unicode_literals

from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from .views import UserOrgsEndpoint, FlowStepEndpoint, CreateAccountView
from .views import ManageAccountsListEndpoint, ManageAccountsActionEndpoint, DeviceTokenEndpoint

from .views import RootView, ExplorerView, AuthenticateView, BroadcastsEndpoint, ChannelsEndpoint, ChannelEventsEndpoint
from .views import CampaignsEndpoint, CampaignEventsEndpoint, ContactsEndpoint, DefinitionsEndpoint, FlowsEndpoint
from .views import FieldsEndpoint, FlowStartsEndpoint, GroupsEndpoint, LabelsEndpoint, MediaEndpoint, MessagesEndpoint
from .views import OrgEndpoint, ResthooksEndpoint, ResthookEventsEndpoint, ResthookSubscribersEndpoint, RunsEndpoint
from .views import BoundariesEndpoint, ContactActionsEndpoint, MessageActionsEndpoint, CustomEndpoints, MeEndpoint
from .views import RecoveryPasswordView


urlpatterns = [
    url(r'^$', RootView.as_view(), name='api.v3'),
    url(r'^explorer/$', ExplorerView.as_view(), name='api.v3.explorer'),

    # these endpoints are retained for Android Surveyor clients
    url(r'^authenticate$', AuthenticateView.as_view(), name='api.v3.authenticate'),
    url(r'^me$', MeEndpoint.as_view(), name='api.v3.me'),
    url(r'^create_account$', CreateAccountView.as_view(), name='api.v3.create_account'),
    url(r'^recovery_password$', RecoveryPasswordView.as_view(), name='api.v3.recovery_password'),
    url(r'^user/orgs$', UserOrgsEndpoint.as_view(), name='api.v3.user_orgs'),
    url(r'^user/device_token$', DeviceTokenEndpoint.as_view(), name='api.v3.device_token'),
    url(r'^manage_accounts/list$', ManageAccountsListEndpoint.as_view(), name='api.v3.manage_accounts_list'),
    url(r'^manage_accounts/action/(?P<action>approve|deny)$', ManageAccountsActionEndpoint.as_view(), name='api.v3.manage_accounts_action'),
    url(r'^custom_endpoints$', CustomEndpoints.as_view(), name='api.v3.custom_endpoints'),

    # ========== endpoints A-Z ===========
    url(r'^boundaries$', BoundariesEndpoint.as_view(), name='api.v3.boundaries'),
    url(r'^broadcasts$', BroadcastsEndpoint.as_view(), name='api.v3.broadcasts'),
    url(r'^campaigns$', CampaignsEndpoint.as_view(), name='api.v3.campaigns'),
    url(r'^campaign_events$', CampaignEventsEndpoint.as_view(), name='api.v3.campaign_events'),
    url(r'^channels$', ChannelsEndpoint.as_view(), name='api.v3.channels'),
    url(r'^channel_events$', ChannelEventsEndpoint.as_view(), name='api.v3.channel_events'),
    url(r'^contacts$', ContactsEndpoint.as_view(), name='api.v3.contacts'),
    url(r'^contact_actions$', ContactActionsEndpoint.as_view(), name='api.v3.contact_actions'),
    url(r'^definitions$', DefinitionsEndpoint.as_view(), name='api.v3.definitions'),
    url(r'^fields$', FieldsEndpoint.as_view(), name='api.v3.fields'),
    url(r'^flow_starts$', FlowStartsEndpoint.as_view(), name='api.v3.flow_starts'),
    url(r'^flows$', FlowsEndpoint.as_view(), name='api.v3.flows'),
    url(r'^groups$', GroupsEndpoint.as_view(), name='api.v3.groups'),
    url(r'^labels$', LabelsEndpoint.as_view(), name='api.v3.labels'),
    url(r'^media$', MediaEndpoint.as_view(), name='api.v3.media'),
    url(r'^messages$', MessagesEndpoint.as_view(), name='api.v3.messages'),
    url(r'^message_actions$', MessageActionsEndpoint.as_view(), name='api.v3.message_actions'),
    url(r'^org$', OrgEndpoint.as_view(), name='api.v3.org'),
    url(r'^resthooks$', ResthooksEndpoint.as_view(), name='api.v3.resthooks'),
    url(r'^resthook_events$', ResthookEventsEndpoint.as_view(), name='api.v3.resthook_events'),
    url(r'^resthook_subscribers$', ResthookSubscribersEndpoint.as_view(), name='api.v3.resthook_subscribers'),
    url(r'^runs$', RunsEndpoint.as_view(), name='api.v3.runs'),
    url(r'^steps$', FlowStepEndpoint.as_view(), name='api.v3.steps'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'api'])
