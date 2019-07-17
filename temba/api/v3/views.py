from __future__ import absolute_import, unicode_literals

import random
import six
import string
import itertools

from django import forms
from django.contrib.auth import authenticate
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import Prefetch
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from django.views.decorators.csrf import csrf_exempt

from smartmin.views import SmartFormView
from smartmin.email import build_email_context
from smartmin.users.models import RecoveryToken, FailedLogin
from rest_framework import views, status, generics
from rest_framework.response import Response
from rest_framework.reverse import reverse

from temba.api.models import APIToken, api_token, DeviceToken
from temba.api.v1.views import ContactEndpoint as ContactEndpointV1, FlowStepEndpoint as FlowStepEndpointV1
from temba.api.v2.views import WriteAPIMixin, BaseAPIView, ListAPIMixin, SSLPermission, IsAuthenticated, DeleteAPIMixin
from temba.api.v2.views import AuthenticateView as AuthenticateEndpointV2
from temba.api.v2.views import RunsEndpoint as RunsEndpointV2
from temba.api.v2.views import ExplorerView as ExplorerViewV2
from temba.api.v2.views import BoundariesEndpoint as BoundariesEndpointV2
from temba.api.v2.views import BroadcastsEndpoint as BroadcastsEndpointV2
from temba.api.v2.views import CampaignsEndpoint as CampaignsEndpointV2
from temba.api.v2.views import CampaignEventsEndpoint as CampaignEventsEndpointV2
from temba.api.v2.views import ChannelsEndpoint as ChannelsEndpointV2
from temba.api.v2.views import ChannelEventsEndpoint as ChannelEventsEndpointV2
from temba.api.v2.views import ContactActionsEndpoint as ContactActionsEndpointV2
from temba.api.v2.views import DefinitionsEndpoint as DefinitionsEndpointV2
from temba.api.v2.views import FieldsEndpoint as FieldsEndpointV2
from temba.api.v2.views import FlowsEndpoint as FlowsEndpointV2
from temba.api.v2.views import FlowStartsEndpoint as FlowStartsEndpointV2
from temba.api.v2.views import GroupsEndpoint as GroupsEndpointV2
from temba.api.v2.views import LabelsEndpoint as LabelsEndpointV2
from temba.api.v2.views import MediaEndpoint as MediaEndpointV2
from temba.api.v2.views import MessagesEndpoint as MessagesEndpointV2
from temba.api.v2.views import MessageActionsEndpoint as MessageActionsEndpointV2
from temba.api.v2.views import OrgEndpoint as OrgEndpointV2
from temba.api.v2.views import ResthooksEndpoint as ResthooksEndpointV2
from temba.api.v2.views import ResthookSubscribersEndpoint as ResthookSubscribersEndpointV2
from temba.api.v2.views import ResthookEventsEndpoint as ResthookEventsEndpointV2
from temba.campaigns.models import Campaign
from temba.contacts.models import Contact, ContactField
from temba.flows.models import Flow, FlowStart, FlowStep, RuleSet
from temba.orgs.models import get_user_orgs, Org
from temba.utils import str_to_bool, splitting_getlist

from .serializers import FlowRunReadSerializer, FlowReadSerializer, FlowRunWriteSerializer
from ..tasks import send_account_manage_email_task, send_recovery_mail, push_notification_to_fcm
from ..support import InvalidQueryError


def get_apitoken_from_auth(auth):
    token = auth.split(' ')[-1]
    api_token = APIToken.objects.filter(key=token).only('org').first()
    return api_token if api_token else None


class BaseAPIViewV3(BaseAPIView):
    """
    Base class of all our API endpoints
    """
    throttle_scope = 'v3'

    @transaction.non_atomic_requests
    def dispatch(self, request, *args, **kwargs):
        return super(BaseAPIViewV3, self).dispatch(request, *args, **kwargs)


class RootView(views.APIView):
    """
    We provide a RESTful JSON API for you to interact with your data from outside applications. The following endpoints
    are available:

     * [/api/v3/boundaries](/api/v3/boundaries) - to list administrative boundaries
     * [/api/v3/broadcasts](/api/v3/broadcasts) - to list and send message broadcasts
     * [/api/v3/campaigns](/api/v3/campaigns) - to list, create, or update campaigns
     * [/api/v3/campaign_events](/api/v3/campaign_events) - to list, create, update or delete campaign events
     * [/api/v3/channels](/api/v3/channels) - to list channels
     * [/api/v3/channel_events](/api/v3/channel_events) - to list channel events
     * [/api/v3/contacts](/api/v3/contacts) - to list, create, update or delete contacts
     * [/api/v3/contact_actions](/api/v3/contact_actions) - to perform bulk contact actions
     * [/api/v3/create_account](/api/v3/custom_endpoints#create-account) - to create an account through multipart form request
     * [/api/v3/definitions](/api/v3/definitions) - to export flow definitions, campaigns, and triggers
     * [/api/v3/fields](/api/v3/fields) - to list, create or update contact fields
     * [/api/v3/flow_starts](/api/v3/flow_starts) - to list flow starts and start contacts in flows
     * [/api/v3/flows](/api/v3/flows) - to list flows
     * [/api/v3/groups](/api/v3/groups) - to list, create, update or delete contact groups
     * [/api/v3/labels](/api/v3/labels) - to list, create, update or delete message labels
     * [/api/v3/me](/api/v3/me) - to view data about the user logged
     * [/api/v3/media](/api/v3/media) - to upload medias to org
     * [/api/v3/messages](/api/v3/messages) - to list messages
     * [/api/v3/message_actions](/api/v3/message_actions) - to perform bulk message actions
     * [/api/v3/manage_accounts/list](/api/v3/custom_endpoints#manage-accounts) - to list accounts pending of approbation
     * [/api/v3/manage_accounts/action/approve](/api/v3/manage_accounts/action/approve) - to perform bulk approve actions
     * [/api/v3/manage_accounts/action/deny](/api/v3/manage_accounts/action/deny) - to perform bulk deny actions
     * [/api/v3/org](/api/v3/org) - to view your org
     * [/api/v3/recovery_password](/api/v3/custom_endpoints#recovery-password) - to recovery the password through multipart form request
     * [/api/v3/runs](/api/v3/runs) - to list flow runs
     * [/api/v3/resthooks](/api/v3/resthooks) - to list resthooks
     * [/api/v3/resthook_events](/api/v3/resthook_events) - to list resthook events
     * [/api/v3/resthook_subscribers](/api/v3/resthook_subscribers) - to list, create or delete subscribers on your resthooks
     * [/api/v3/steps](/api/v3/steps) - to create runs on Surveyor app
     * [/api/v3/user/device_token](/api/v3/user/device_token) - to add device token to user
     * [/api/v3/user/orgs](/api/v3/custom_endpoints#user-orgs) - to list orgs of the user

    To use the endpoint simply append _.json_ to the URL. For example [/api/v3/flows](/api/v3/flows) will return the
    documentation for that endpoint but a request to [/api/v3/flows.json](/api/v3/flows.json) will return a JSON list of
    flow resources.

    You may wish to use the [API Explorer](/api/v3/explorer) to interactively experiment with the API.

    ## Verbs

    All endpoints follow standard REST conventions. You can list a set of resources by making a `GET` request to the
    endpoint, create or update resources by making a `POST` request, or delete a resource with a `DELETE` request.

    ## Status Codes

    The success or failure of requests is represented by status codes as well as a message in the response body:

     * **200**: A list or update request was successful.
     * **201**: A resource was successfully created (only returned for `POST` requests).
     * **204**: An empty response - used for both successful `DELETE` requests and `POST` requests that update multiple
                resources.
     * **400**: The request failed due to invalid parameters. Do not retry with the same values, and the body of the
                response will contain details.
     * **403**: You do not have permission to access this resource.
     * **404**: The resource was not found (returned by `POST` and `DELETE` methods).
     * **429**: You have exceeded the rate limit for this endpoint (see below).

    ## Rate Limiting

    All endpoints are subject to rate limiting. If you exceed the number of allowed requests in a given time window, you
    will get a response with status code 429. The response will also include a header called 'Retry-After' which will
    specify the number of seconds that you should wait for before making further requests.

    The rate limit for all endpoints is 2,500 requests per hour. It is important to honor the Retry-After header when
    encountering 429 responses as the limit is subject to change without notice.

    ## Date Values

    Many endpoints either return datetime values or can take datatime parameters. The values returned will always be in
    UTC, in the following format: `YYYY-MM-DDThh:mm:ss.ssssssZ`, where `ssssss` is the number of microseconds and
    `Z` denotes the UTC timezone.

    When passing datetime values as parameters, you should use this same format, e.g. `2016-10-13T11:54:32.525277Z`.

    ## URN Values

    We use URNs (Uniform Resource Names) to describe the different ways of communicating with a contact. These can be
    phone numbers, Twitter handles etc. For example a contact might have URNs like:

     * **tel:+250788123123**
     * **twitter:jack**
     * **mailto:jack@example.com**

    Phone numbers should always be given in full [E164 format](http://en.wikipedia.org/wiki/E.164).

    ## Translatable Values

    Some endpoints return or accept text fields that may be translated into different languages. These should be objects
    with ISO-639-2 language codes as keys, e.g. `{"eng": "Hello", "fre": "Bonjour"}`

    ## Authentication

    You must authenticate all calls by including an `Authorization` header with your API token. If you are logged in,
    your token will be visible at the top of this page. The Authorization header should look like:

        Authorization: Token YOUR_API_TOKEN

    For security reasons, all calls must be made using HTTPS.

    ## Clients

    There is an official [Python client library](https://github.com/rapidpro/rapidpro-python) which we recommend for all
    Python users of the API.
    """
    permission_classes = (SSLPermission, IsAuthenticated)

    def get(self, request, *args, **kwargs):
        return Response({
            'boundaries': reverse('api.v3.boundaries', request=request),
            'broadcasts': reverse('api.v3.broadcasts', request=request),
            'campaigns': reverse('api.v3.campaigns', request=request),
            'campaign_events': reverse('api.v3.campaign_events', request=request),
            'channels': reverse('api.v3.channels', request=request),
            'channel_events': reverse('api.v3.channel_events', request=request),
            'contacts': reverse('api.v3.contacts', request=request),
            'contact_actions': reverse('api.v3.contact_actions', request=request),
            'definitions': reverse('api.v3.definitions', request=request),
            'device_token': reverse('api.v3.device_token', request=request),
            'fields': reverse('api.v3.fields', request=request),
            'flow_starts': reverse('api.v3.flow_starts', request=request),
            'flows': reverse('api.v3.flows', request=request),
            'groups': reverse('api.v3.groups', request=request),
            'labels': reverse('api.v3.labels', request=request),
            'messages': reverse('api.v3.messages', request=request),
            'message_actions': reverse('api.v3.message_actions', request=request),
            'manage_accounts_action': reverse('api.v3.manage_accounts_action', args=['approve'], request=request),
            'org': reverse('api.v3.org', request=request),
            'resthooks': reverse('api.v3.resthooks', request=request),
            'resthook_events': reverse('api.v3.resthook_events', request=request),
            'resthook_subscribers': reverse('api.v3.resthook_subscribers', request=request),
            'runs': reverse('api.v3.runs', request=request),
            'steps': reverse('api.v3.steps', request=request),
        })


class AuthenticateView(AuthenticateEndpointV2):

    def form_valid(self, form, *args, **kwargs):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        role_code = form.cleaned_data.get('role')

        user = authenticate(username=username, password=password)
        if user:
            if not user.is_active:
                result = JsonResponse(dict(error=403,
                                           message=_('This account is inactive. Please contact your administrator.')),
                                      safe=False, status=status.HTTP_403_FORBIDDEN)
            else:
                role = APIToken.get_role_from_code(role_code)

                if role:
                    token = api_token(user)
                    token_obj = APIToken.objects.filter(key=token).only('org', 'key').first() if token else None
                    if (not token) or (token and token_obj.org.is_suspended()):
                        result = JsonResponse(dict(error=403,
                                                   message=_('No organizations associated with this account or your '
                                                             'organization is inactive. Please contact your '
                                                             'administrator.')),
                                              safe=False, status=status.HTTP_403_FORBIDDEN)
                    else:
                        result = JsonResponse(dict(token=token), safe=False)
                else:  # pragma: needs cover
                    result = HttpResponse(status=status.HTTP_403_FORBIDDEN)
        else:  # pragma: needs cover
            result = JsonResponse(dict(error=403,
                                       message=_('Not able to authenticate, verify either the email and password '
                                                 'are correct')),
                                  safe=False, status=status.HTTP_403_FORBIDDEN)
        return result


class ExplorerView(ExplorerViewV2):
    """
    Explorer view which lets users experiment with endpoints against their own data
    """
    template_name = "api/v3/api_explorer.html"

    def get_context_data(self, **kwargs):
        context = super(ExplorerView, self).get_context_data(**kwargs)
        context['endpoints'] = [
            BoundariesEndpoint.get_read_explorer(),
            BroadcastsEndpoint.get_read_explorer(),
            BroadcastsEndpoint.get_write_explorer(),
            CampaignsEndpoint.get_read_explorer(),
            CampaignsEndpoint.get_write_explorer(),
            CampaignEventsEndpoint.get_read_explorer(),
            CampaignEventsEndpoint.get_write_explorer(),
            CampaignEventsEndpoint.get_delete_explorer(),
            ChannelsEndpoint.get_read_explorer(),
            ChannelEventsEndpoint.get_read_explorer(),
            ContactsEndpoint.get_read_explorer(),
            ContactsEndpoint.get_write_explorer(),
            ContactsEndpoint.get_delete_explorer(),
            ContactActionsEndpoint.get_write_explorer(),
            DefinitionsEndpoint.get_read_explorer(),
            FieldsEndpoint.get_read_explorer(),
            FieldsEndpoint.get_write_explorer(),
            FlowsEndpoint.get_read_explorer(),
            FlowStartsEndpoint.get_read_explorer(),
            FlowStartsEndpoint.get_write_explorer(),
            GroupsEndpoint.get_read_explorer(),
            GroupsEndpoint.get_write_explorer(),
            GroupsEndpoint.get_delete_explorer(),
            LabelsEndpoint.get_read_explorer(),
            LabelsEndpoint.get_write_explorer(),
            LabelsEndpoint.get_delete_explorer(),
            ManageAccountsListEndpoint.get_read_explorer(),
            ManageAccountsActionEndpoint.get_approve_write_explorer(),
            ManageAccountsActionEndpoint.get_deny_write_explorer(),
            MeEndpoint.get_read_explorer(),
            MeEndpoint.get_write_explorer(),
            MessagesEndpoint.get_read_explorer(),
            MessageActionsEndpoint.get_write_explorer(),
            OrgEndpoint.get_read_explorer(),
            ResthooksEndpoint.get_read_explorer(),
            ResthookEventsEndpoint.get_read_explorer(),
            ResthookSubscribersEndpoint.get_read_explorer(),
            ResthookSubscribersEndpoint.get_write_explorer(),
            ResthookSubscribersEndpoint.get_delete_explorer(),
            RunsEndpoint.get_read_explorer(),
            FlowStepEndpoint.get_write_explorer(),
            UserOrgsEndpoint.get_read_explorer(),
            DeviceTokenEndpoint.get_write_explorer(),
        ]
        return context


class BoundariesEndpoint(BoundariesEndpointV2):
    """
    This endpoint allows you to list the administrative boundaries for the country associated with your account,
    along with the simplified GPS geometry for those boundaries in GEOJSON format.

    ## Listing Boundaries

    A `GET` returns the boundaries for your organization with the following fields. To include geometry,
    specify `geometry=true`.

      * **osm_id** - the OSM ID for this boundary prefixed with the element type (string)
      * **name** - the name of the administrative boundary (string)
      * **parent** - the id of the containing parent of this boundary or null if this boundary is a country (string)
      * **level** - the level: 0 for country, 1 for state, 2 for district (int)
      * **geometry** - the geometry for this boundary, which will usually be a MultiPolygon (GEOJSON)

    **Note that including geometry may produce a very large result so it is recommended to cache the results on the
    client side.**

    Example:

        GET /api/v3/boundaries.json?geometry=true

    Response is a list of the boundaries on your account

        {
            "next": null,
            "previous": null,
            "results": [
            {
                "osm_id": "1708283",
                "name": "Kigali City",
                "parent": {"osm_id": "171496", "name": "Rwanda"},
                "level": 1,
                "aliases": ["Kigari"],
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [
                            [
                                [7.5251021, 5.0504713],
                                [7.5330272, 5.0423498]
                            ]
                        ]
                    ]
                }
            },
            ...
        }

    """
    @classmethod
    def get_read_explorer(cls):
        source_object = BoundariesEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.boundaries')
        return source_object


class BroadcastsEndpoint(BroadcastsEndpointV2):
    """
    This endpoint allows you to send new message broadcasts and list existing broadcasts in your account.

    ## Listing Broadcasts

    A `GET` returns the outgoing message activity for your organization, listing the most recent messages first.

     * **id** - the id of the broadcast (int), filterable as `id`.
     * **urns** - the URNs that received the broadcast (array of strings)
     * **contacts** - the contacts that received the broadcast (array of objects)
     * **groups** - the groups that received the broadcast (array of objects)
     * **text** - the message text (string or translations object)
     * **created_on** - when this broadcast was either created (datetime) (filterable as `before` and `after`).

    Example:

        GET /api/v3/broadcasts.json

    Response is a list of recent broadcasts:

        {
            "next": null,
            "previous": null,
            "results": [
                {
                    "id": 123456,
                    "urns": ["tel:+250788123123", "tel:+250788123124"],
                    "contacts": [{"uuid": "09d23a05-47fe-11e4-bfe9-b8f6b119e9ab", "name": "Joe"}]
                    "groups": [],
                    "text": "hello world",
                    "created_on": "2013-03-02T17:28:12.123456Z"
                },
                ...

    ## Sending Broadcasts

    A `POST` allows you to create and send new broadcasts, with the following JSON data:

      * **text** - the text of the message to send (string, limited to 640 characters)
      * **urns** - the URNs of contacts to send to (array of up to 100 strings, optional)
      * **contacts** - the UUIDs of contacts to send to (array of up to 100 strings, optional)
      * **groups** - the UUIDs of contact groups to send to (array of up to 100 strings, optional)
      * **channel** - the UUID of the channel to use. Contacts which can't be reached with this channel are ignored (string, optional)

    Example:

        POST /api/v3/broadcasts.json
        {
            "urns": ["tel:+250788123123", "tel:+250788123124"],
            "contacts": ["09d23a05-47fe-11e4-bfe9-b8f6b119e9ab"],
            "text": "hello world"
        }

    You will receive a response containing the message broadcast created:

        {
            "id": 1234,
            "urns": ["tel:+250788123123", "tel:+250788123124"],
            "contacts": [{"uuid": "09d23a05-47fe-11e4-bfe9-b8f6b119e9ab", "name": "Joe"}]
            "groups": [],
            "text": "hello world",
            "created_on": "2013-03-02T17:28:12.123456Z"
        }
    """
    @classmethod
    def get_read_explorer(cls):
        source_object = BroadcastsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.broadcasts')
        return source_object

    @classmethod
    def get_write_explorer(cls):
        source_object = BroadcastsEndpointV2.get_write_explorer()
        source_object['url'] = reverse('api.v3.broadcasts')
        return source_object


class CampaignsEndpoint(CampaignsEndpointV2):
    """
    This endpoint allows you to list campaigns in your account.

    ## Listing Campaigns

    A `GET` returns the campaigns, listing the most recently created campaigns first.

     * **uuid** - the UUID of the campaign (string), filterable as `uuid`.
     * **name** - the name of the campaign (string).
     * **archived** - whether this campaign is archived (boolean)
     * **group** - the group this campaign operates on (object).
     * **created_on** - when the campaign was created (datetime), filterable as `before` and `after`.

    Example:

        GET /api/v3/campaigns.json

    Response is a list of the campaigns on your account

        {
            "next": null,
            "previous": null,
            "results": [
            {
                "uuid": "f14e4ff0-724d-43fe-a953-1d16aefd1c00",
                "name": "Reminders",
                "archived": false,
                "group": {"uuid": "7ae473e8-f1b5-4998-bd9c-eb8e28c92fa9", "name": "Reporters"},
                "created_on": "2013-08-19T19:11:21.088Z"
            },
            ...
        }

    ## Adding Campaigns

    A **POST** can be used to create a new campaign, by sending the following data. Don't specify a UUID as this will be
    generated for you.

    * **name** - the name of the campaign (string, required)
    * **group** - the UUID of the contact group this campaign will be run against (string, required)

    Example:

        POST /api/v3/campaigns.json
        {
            "name": "Reminders",
            "group": "7ae473e8-f1b5-4998-bd9c-eb8e28c92fa9"
        }

    You will receive a campaign object as a response if successful:

        {
            "uuid": "f14e4ff0-724d-43fe-a953-1d16aefd1c00",
            "name": "Reminders",
            "archived": false,
            "group": {"uuid": "7ae473e8-f1b5-4998-bd9c-eb8e28c92fa9", "name": "Reporters"},
            "created_on": "2013-08-19T19:11:21.088Z"
        }

    ## Updating Campaigns

    A **POST** can also be used to update an existing campaign if you specify its UUID in the URL.

    Example:

        POST /api/v3/campaigns.json?uuid=f14e4ff0-724d-43fe-a953-1d16aefd1c00
        {
            "name": "Reminders II",
            "group": "7ae473e8-f1b5-4998-bd9c-eb8e28c92fa9"
        }

    """
    @classmethod
    def get_read_explorer(cls):
        source_object = CampaignsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.campaigns')
        return source_object

    @classmethod
    def get_write_explorer(cls):
        source_object = CampaignsEndpointV2.get_write_explorer()
        source_object['url'] = reverse('api.v3.campaigns')
        return source_object


class CampaignEventsEndpoint(CampaignEventsEndpointV2):
    """
    This endpoint allows you to list campaign events in your account.

    ## Listing Campaign Events

    A `GET` returns the campaign events, listing the most recently created events first.

     * **uuid** - the UUID of the campaign (string), filterable as `uuid`.
     * **campaign** - the UUID and name of the campaign (object), filterable as `campaign` with UUID.
     * **relative_to** - the key and label of the date field this event is based on (object).
     * **offset** - the offset from our contact field (positive or negative integer).
     * **unit** - the unit for our offset (one of "minutes, "hours", "days", "weeks").
     * **delivery_hour** - the hour of the day to deliver the message (integer 0-24, -1 indicates send at the same hour as the contact field).
     * **message** - the message to send to the contact if this is a message event (string or translations object)
     * **flow** - the UUID and name of the flow if this is a flow event (object).
     * **created_on** - when the event was created (datetime).

    Example:

        GET /api/v3/campaign_events.json

    Response is a list of the campaign events on your account

        {
            "next": null,
            "previous": null,
            "results": [
            {
                "uuid": "f14e4ff0-724d-43fe-a953-1d16aefd1c00",
                "campaign": {"uuid": "f14e4ff0-724d-43fe-a953-1d16aefd1c00", "name": "Reminders"},
                "relative_to": {"key": "registration", "label": "Registration Date"},
                "offset": 7,
                "unit": "days",
                "delivery_hour": 9,
                "flow": {"uuid": "09d23a05-47fe-11e4-bfe9-b8f6b119e9ab", "name": "Survey"},
                "message": null,
                "created_on": "2013-08-19T19:11:21.088Z"
            },
            ...
        }

    ## Adding Campaign Events

    A **POST** can be used to create a new campaign event, by sending the following data. Don't specify a UUID as this
    will be generated for you.

    * **campaign** - the UUID of the campaign this event should be part of (string, can't be changed for existing events)
    * **relative_to** - the field key that this event will be relative to (string)
    * **offset** - the offset from our contact field (positive or negative integer)
    * **unit** - the unit for our offset (one of "minutes", "hours", "days" or "weeks")
    * **delivery_hour** - the hour of the day to deliver the message (integer 0-24, -1 indicates send at the same hour as the field)
    * **message** - the message to send to the contact (string, required if flow is not specified)
    * **flow** - the UUID of the flow to start the contact down (string, required if message is not specified)

    Example:

        POST /api/v3/campaign_events.json
        {
            "campaign": "f14e4ff0-724d-43fe-a953-1d16aefd1c00",
            "relative_to": "last_hit",
            "offset": 160,
            "unit": "weeks",
            "delivery_hour": -1,
            "message": "Feeling sick and helpless, lost the compass where self is."
        }

    You will receive an event object as a response if successful:

        {
            "uuid": "6a6d7531-6b44-4c45-8c33-957ddd8dfabc",
            "campaign": {"uuid": "f14e4ff0-724d-43fe-a953-1d16aefd1c00", "name": "Hits"},
            "relative_to": "last_hit",
            "offset": 160,
            "unit": "W",
            "delivery_hour": -1,
            "message": {"eng": "Feeling sick and helpless, lost the compass where self is."},
            "flow": null,
            "created_on": "2013-08-19T19:11:21.088453Z"
        }

    ## Updating Campaign Events

    A **POST** can also be used to update an existing campaign event if you specify its UUID in the URL.

    Example:

        POST /api/v3/campaign_events.json?uuid=6a6d7531-6b44-4c45-8c33-957ddd8dfabc
        {
            "relative_to": "last_hit",
            "offset": 100,
            "unit": "weeks",
            "delivery_hour": -1,
            "message": "Feeling sick and helpless, lost the compass where self is."
        }

    ## Deleting Campaign Events

    A **DELETE** can be used to delete a campaign event if you specify its UUID in the URL.

    Example:

        DELETE /api/v3/campaign_events.json?uuid=6a6d7531-6b44-4c45-8c33-957ddd8dfabc

    You will receive either a 204 response if an event was deleted, or a 404 response if no matching event was found.

    """

    @classmethod
    def get_read_explorer(cls):
        source_object = CampaignEventsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.campaign_events')
        return source_object

    @classmethod
    def get_write_explorer(cls):
        source_object = CampaignEventsEndpointV2.get_write_explorer()
        source_object['url'] = reverse('api.v3.campaign_events')
        return source_object

    @classmethod
    def get_delete_explorer(cls):
        source_object = CampaignEventsEndpointV2.get_delete_explorer()
        source_object['url'] = reverse('api.v3.campaign_events')
        return source_object


class ChannelsEndpoint(ChannelsEndpointV2):
    """
    This endpoint allows you to list channels in your account.

    ## Listing Channels

    A **GET** returns the list of channels for your organization, in the order of last created.  Note that for
    Android devices, all status information is as of the last time it was seen and can be null before the first sync.

     * **uuid** - the UUID of the channel (string), filterable as `uuid`.
     * **name** - the name of the channel (string).
     * **address** - the address (e.g. phone number, Twitter handle) of the channel (string), filterable as `address`.
     * **country** - which country the sim card for this channel is registered for (string, two letter country code).
     * **device** - information about the device if this is an Android channel:
        * **name** - the name of the device (string).
        * **power_level** - the power level of the device (int).
        * **power_status** - the power status, either ```STATUS_DISCHARGING``` or ```STATUS_CHARGING``` (string).
        * **power_source** - the source of power as reported by Android (string).
        * **network_type** - the type of network the device is connected to as reported by Android (string).
     * **last_seen** - the datetime when this channel was last seen (datetime).
     * **created_on** - the datetime when this channel was created (datetime).

    Example:

        GET /api/v3/channels.json

    Response containing the channels for your organization:

        {
            "next": null,
            "previous": null,
            "results": [
            {
                "uuid": "09d23a05-47fe-11e4-bfe9-b8f6b119e9ab",
                "name": "Android Phone",
                "address": "+250788123123",
                "country": "RW",
                "device": {
                    "name": "Nexus 5X",
                    "power_level": 99,
                    "power_status": "STATUS_DISCHARGING",
                    "power_source": "BATTERY",
                    "network_type": "WIFI",
                },
                "last_seen": "2016-03-01T05:31:27.456",
                "created_on": "2014-06-23T09:34:12.866",
            }]
        }

    """
    @classmethod
    def get_read_explorer(cls):
        source_object = ChannelsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.channels')
        return source_object


class ChannelEventsEndpoint(ChannelEventsEndpointV2):
    """
    This endpoint allows you to list channel events in your account.

    ## Listing Channel Events

    A **GET** returns the channel events for your organization, most recent first.

     * **id** - the ID of the event (int), filterable as `id`.
     * **channel** - the UUID and name of the channel that handled this call (object).
     * **type** - the type of event (one of "call-in", "call-in-missed", "call-out", "call-out-missed").
     * **contact** - the UUID and name of the contact (object), filterable as `contact` with UUID.
     * **extra** - any extra attributes collected for this event
     * **occurred_on** - when this event happened on the channel (datetime).
     * **created_on** - when this event was created (datetime), filterable as `before` and `after`.

    Example:

        GET /api/v3/channel_events.json

    Response:

        {
            "next": null,
            "previous": null,
            "results": [
            {
                "id": 4,
                "channel": {"uuid": "9a8b001e-a913-486c-80f4-1356e23f582e", "name": "Nexmo"},
                "type": "call-in"
                "contact": {"uuid": "d33e9ad5-5c35-414c-abd4-e7451c69ff1d", "name": "Bob McFlow"},
                "extra": { "duration": 606 },
                "occurred_on": "2013-02-27T09:06:12.123"
                "created_on": "2013-02-27T09:06:15.456"
            },
            ...

    """
    @classmethod
    def get_read_explorer(cls):
        source_object = ChannelEventsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.channel_events')
        return source_object


class ContactsEndpoint(ContactEndpointV1, DeleteAPIMixin, BaseAPIViewV3):
    """
    ## Adding a Contact

    You can add a new contact to your account, or update the fields on a contact by sending a **POST** request to this
    URL with the following JSON data:

    * **uuid** - the UUID of the contact to update (string) (optional, new contact created if not present)
    * **name** - the full name of the contact (string, optional)
    * **language** - the preferred language for the contact (3 letter iso code, optional)
    * **urns** - a list of URNs you want associated with the contact (string array)
    * **group_uuids** - a list of the UUIDs of any groups this contact is part of (string array, optional)
    * **fields** - a JSON dictionary of contact fields you want to set or update on this contact (JSON, optional)

    Example:

        POST /api/v3/contacts.json
        {
            "name": "Ben Haggerty",
            "language": "eng",
            "urns": ["tel:+250788123123", "twitter:ben"],
            "group_uuids": ["6685e933-26e1-4363-a468-8f7268ab63a9", "1281f10a-d5b3-4580-a0fe-92adb97c2d1a"],
            "fields": {
              "nickname": "Macklemore",
              "side_kick": "Ryan Lewis"
            }
        }

    You will receive a contact object as a response if successful:

        {
            "uuid": "09d23a05-47fe-11e4-bfe9-b8f6b119e9ab",
            "name": "Ben Haggerty",
            "language": "eng",
            "urns": ["tel:+250788123123", "twitter:ben"],
            "group_uuids": ["6685e933-26e1-4363-a468-8f7268ab63a9", "1281f10a-d5b3-4580-a0fe-92adb97c2d1a"],
            "fields": {
              "nickname": "Macklemore",
              "side_kick": "Ryan Lewis"
            }
            "blocked": false,
            "failed": false
        }

    ## Updating Contacts

    You can update contacts in the same manner as adding them but we recommend you pass in the UUID for the contact
    as a way of specifying which contact to update. Note that when you pass in the contact UUID and ```urns```, all
    existing URNs will be evaluated against this new set and updated accordingly.

    ## Listing Contacts

    A **GET** returns the list of contacts for your organization, in the order of last activity date. You can return
    only deleted contacts by passing the "?deleted=true" parameter to your call.

    * **uuid** - the unique identifier for this contact (string) (filterable: ```uuid``` repeatable)
    * **name** - the name of this contact (string, optional)
    * **language** - the preferred language of this contact (string, optional)
    * **urns** - the URNs associated with this contact (string array) (filterable: ```urns```)
    * **group_uuids** - the UUIDs of any groups this contact is part of (string array, optional) (filterable: ```group_uuids``` repeatable)
    * **fields** - any contact fields on this contact (JSON, optional)
    * **after** - only contacts which have changed on this date or after (string) ex: 2012-01-28T18:00:00.000
    * **before** - only contacts which have been changed on this date or before (string) ex: 2012-01-28T18:00:00.000

    Example:

        GET /api/v3/contacts.json

    Response containing the contacts for your organization:

        {
            "count": 1,
            "next": null,
            "previous": null,
            "results": [
            {
                "uuid": "09d23a05-47fe-11e4-bfe9-b8f6b119e9ab",
                "name": "Ben Haggerty",
                "language": null,
                "urns": [
                  "tel:+250788123123"
                ],
                "group_uuids": ["6685e933-26e1-4363-a468-8f7268ab63a9", "1281f10a-d5b3-4580-a0fe-92adb97c2d1a"],
                "fields": {
                  "nickname": "Macklemore",
                  "side_kick": "Ryan Lewis"
                }
            }]
        }
    ## Deleting Contacts

    A **DELETE** can also be used to delete an existing contact if you specify either its UUID or one of its URNs in the
    URL.

    Examples:

        DELETE /api/v3/contacts.json?uuid=27fb583b-3087-4778-a2b3-8af489bf4a93

        DELETE /api/v3/contacts.json?urn=tel%3A%2B250783835665

    You will receive either a 204 response if a contact was deleted, or a 404 response if no matching contact was found.
    """
    permission = 'contacts.contact_api'
    throttle_scope = 'v3.contacts'
    lookup_params = {'uuid': 'uuid', 'urns': 'urns__identity', 'urn': 'urns__identity'}

    def get_lookup_values(self):
        """
        Extracts lookup_params from the request URL, e.g. {"uuid": "123..."}
        """
        lookup_values = {}
        for param, field in six.iteritems(self.lookup_params):
            if param in self.request.query_params:
                param_value = self.request.query_params[param]

                # try to normalize URN lookup values
                if param in ['urn', 'urns']:
                    param_value = self.normalize_urn(param_value)

                lookup_values[field] = param_value

        if len(lookup_values) > 1:
            raise InvalidQueryError("URL can only contain one of the following parameters: " + ", ".join(self.lookup_params.keys()))

        return lookup_values

    def post_save(self, instance):
        """
        Can be overridden to add custom handling after object creation
        """
        pass

    def post(self, request, *args, **kwargs):
        self.lookup_values = self.get_lookup_values()

        # determine if this is an update of an existing object or a create of a new object
        if self.lookup_values:
            print(self.lookup_values)
            instance = self.get_object()
        else:
            instance = None

        user = request.user
        context = self.get_serializer_context()
        context['lookup_values'] = self.lookup_values
        context['instance'] = instance

        serializer = self.write_serializer_class(instance=instance, data=request.data, context=context, user=user)

        if serializer.is_valid():
            with transaction.atomic():
                output = serializer.save()
                self.post_save(output)
                return self.render_write_response(output, context)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def prepare_for_serialization(self, object_list):
        # initialize caches of all contact fields and URNs
        org = self.request.user.get_org()
        Contact.bulk_cache_initialize(org, object_list)

    def get_serializer_context(self):
        """
        So that we only fetch active contact fields once for all contacts
        """
        context = super(ContactsEndpoint, self).get_serializer_context()
        context['contact_fields'] = ContactField.objects.filter(org=self.request.user.get_org(), is_active=True)
        return context

    def get_object(self):
        queryset = self.get_queryset().filter(**self.lookup_values)

        # don't blow up if posted a URN that doesn't exist - we'll let the serializer create a new contact
        if self.request.method == 'POST' and 'urns__identity' in self.lookup_values:
            return queryset.first()
        else:
            return generics.get_object_or_404(queryset)

    def perform_destroy(self, instance):
        instance.release(self.request.user)

    def render_write_response(self, write_output, context):
        response_serializer = self.serializer_class(instance=write_output, context=context)
        status_code = status.HTTP_200_OK if context['instance'] else status.HTTP_201_CREATED
        return Response(response_serializer.data, status=status_code)

    @classmethod
    def get_read_explorer(cls):
        return {
            'method': "GET",
            'title': "List Contacts",
            'url': reverse('api.v3.contacts'),
            'slug': 'contact-list',
            'params': [dict(name='uuid', required=False,
                            help="One or more UUIDs to filter by. (repeatable) ex: 27fb583b-3087-4778-a2b3-8af489bf4a93"),
                       dict(name='urns', required=False,
                            help="One or more URNs to filter by.  ex: tel:+250788123123,twitter:ben"),
                       dict(name='group_uuids', required=False,
                            help="One or more group UUIDs to filter by. (repeatable) ex: 6685e933-26e1-4363-a468-8f7268ab63a9"),
                       dict(name='after', required=False,
                            help="only contacts which have changed on this date or after.  ex: 2012-01-28T18:00:00.000"),
                       dict(name='before', required=False,
                            help="only contacts which have changed on this date or before. ex: 2012-01-28T18:00:00.000")],
            'example': {'query': "urn=tel%3A%2B250788123123"},
        }

    @classmethod
    def get_write_explorer(cls):
        return {
            'method': "POST",
            'title': "Add or Update Contacts",
            'url': reverse('api.v3.contacts'),
            'slug': 'contact-write',
            'params': [
                {'name': "uuid", 'required': False, 'help': "UUID of the contact to be updated"},
                {'name': "urn", 'required': False, 'help': "URN of the contact to be updated. ex: tel:+250788123123"},
            ],
            'fields': [dict(name='name', required=False,
                            help="The name of the contact.  ex: Ben Haggerty"),
                       dict(name='language', required=False,
                            help="The 3 letter iso code for the preferred language of the contact.  ex: fre, eng"),
                       dict(name='urns', required=True,
                            help='The URNs of the contact.  ex: ["tel:+250788123123"]'),
                       dict(name='group_uuids', required=False,
                            help='The UUIDs of groups this contact should be part of, as a string array.  ex: ["6685e933-26e1-4363-a468-8f7268ab63a9"]'),
                       dict(name='fields', required=False,
                            help='Any fields to set on the contact, as a JSON dictionary. ex: { "Delivery Date": "2012-10-10 5:00" }')],
            'example': {'body': '{ "name": "Ben Haggerty", "groups": ["Top 10 Artists"], "urns": ["tel:+250788123123"] }'},
        }

    @classmethod
    def get_delete_explorer(cls):
        return {
            'method': "DELETE",
            'title': "Delete Contacts",
            'url': reverse('api.v3.contacts'),
            'slug': 'contact-delete',
            'params': [dict(name='uuid', required=False,
                            help="One or more UUIDs to filter by. (repeatable) ex: 27fb583b-3087-4778-a2b3-8af489bf4a93"),
                       dict(name='urn', required=False,
                            help="One URN to filter by.  ex: tel:+250788123123"),
                       dict(name='group_uuids', required=False,
                            help="One or more group UUIDs to filter by. (repeatable) ex: 6685e933-26e1-4363-a468-8f7268ab63a9")],
        }


class ContactActionsEndpoint(ContactActionsEndpointV2):
    """
    ## Bulk Contact Updating

    A **POST** can be used to perform an action on a set of contacts in bulk.

    * **contacts** - the contact UUIDs or URNs (array of up to 100 strings)
    * **action** - the action to perform, a string one of:

        * _add_ - Add the contacts to the given group
        * _remove_ - Remove the contacts from the given group
        * _block_ - Block the contacts
        * _unblock_ - Un-block the contacts
        * _interrupt_ - Interrupt and end any of the contacts' active flow runs
        * _archive_ - Archive all of the contacts' messages
        * _delete_ - Permanently delete the contacts

    * **group** - the UUID or name of a contact group (string, optional)

    Example:

        POST /api/v3/contact_actions.json
        {
            "contacts": ["7acfa6d5-be4a-4bcc-8011-d1bd9dfasff3", "tel:+250783835665"],
            "action": "add",
            "group": "Testers"
        }

    You will receive an empty response with status code 204 if successful.
    """
    @classmethod
    def get_write_explorer(cls):
        source_object = ContactActionsEndpointV2.get_write_explorer()
        source_object['url'] = reverse('api.v3.contact_actions')
        return source_object


class DefinitionsEndpoint(DefinitionsEndpointV2):
    """
    This endpoint allows you to export definitions of flows, campaigns and triggers in your account.

    ## Exporting Definitions

    A **GET** exports a set of flows and campaigns, and can automatically include dependencies for the requested items,
    such as groups, triggers and other flows.

      * **flow** - the UUIDs of flows to include (string, repeatable)
      * **campaign** - the UUIDs of campaigns to include (string, repeatable)
      * **dependencies** - whether to include dependencies (all, flows, none, default: all)

    Example:

        GET /api/v3/definitions.json?flow=f14e4ff0-724d-43fe-a953-1d16aefd1c0b&flow=09d23a05-47fe-11e4-bfe9-b8f6b119e9ab

    Response is a collection of definitions:

        {
          version: 8,
          campaigns: [],
          triggers: [],
          flows: [{
            metadata: {
              "name": "Water Point Survey",
              "uuid": "f14e4ff0-724d-43fe-a953-1d16aefd1c0b",
              "saved_on": "2015-09-23T00:25:50.709164Z",
              "revision": 28,
              "expires": 7880,
              "id": 12712,
            },
            "version": 7,
            "flow_type": "S",
            "base_language": "eng",
            "entry": "87929095-7d13-4003-8ee7-4c668b736419",
            "action_sets": [
              {
                "y": 0,
                "x": 100,
                "destination": "32d415f8-6d31-4b82-922e-a93416d5aa0a",
                "uuid": "87929095-7d13-4003-8ee7-4c668b736419",
                "actions": [
                  {
                    "msg": {
                      "eng": "What is your name?"
                    },
                    "type": "reply"
                  }
                ]
              },
              ...
            ],
            "rule_sets": [
              {
                "uuid": "32d415f8-6d31-4b82-922e-a93416d5aa0a",
                "webhook_action": null,
                "rules": [
                  {
                    "test": {
                      "test": "true",
                      "type": "true"
                    },
                      "category": {
                      "eng": "All Responses"
                    },
                    "destination": null,
                    "uuid": "5fa6e9ae-e78e-4e38-9c66-3acf5e32fcd2",
                    "destination_type": null
                  }
                ],
                "webhook": null,
                "ruleset_type": "wait_message",
                "label": "Name",
                "operand": "@step.value",
                "finished_key": null,
                "y": 162,
                "x": 62,
                "config": {}
              },
              ...
            ]
            }
          }]
        }
    """
    @classmethod
    def get_read_explorer(cls):
        source_object = DefinitionsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.definitions')
        return source_object

    def get(self, request, *args, **kwargs):
        org = request.user.get_org()
        params = request.query_params

        if 'flow_uuid' in params or 'campaign_uuid' in params:  # deprecated
            flow_uuids = splitting_getlist(self.request, 'flow_uuid')
            campaign_uuids = splitting_getlist(self.request, 'campaign_uuid')
        else:
            flow_uuids = params.getlist('flow')
            campaign_uuids = params.getlist('campaign')

        include = params.get('dependencies', 'all')
        if include not in DefinitionsEndpointV2.Depends.__members__:
            raise InvalidQueryError("dependencies must be one of %s" % ', '.join(DefinitionsEndpointV2.Depends.__members__))

        include = DefinitionsEndpointV2.Depends[include]

        if flow_uuids:
            flows = set(Flow.objects.filter(uuid__in=flow_uuids, org=org, is_active=True))
        else:
            flows = set()

        if campaign_uuids:
            campaigns = set(Campaign.objects.filter(uuid__in=campaign_uuids, org=org, is_active=True))
        else:
            campaigns = set()

        if include == DefinitionsEndpointV2.Depends.none:
            components = set(itertools.chain(flows, campaigns))
        elif include == DefinitionsEndpointV2.Depends.flows:
            components = org.resolve_dependencies(flows, campaigns, include_campaigns=False, include_triggers=True)
        else:
            components = org.resolve_dependencies(flows, campaigns, include_campaigns=True, include_triggers=True)

        revision = params.get('revision', None)
        revision = int(revision) if revision else None

        export = org.export_definitions(self.request.branding['link'], components, revision=revision)

        return Response(export, status=status.HTTP_200_OK)


class FieldsEndpoint(FieldsEndpointV2):
    """
    This endpoint allows you to list custom contact fields in your account.

    ## Listing Fields

    A **GET** returns the list of custom contact fields for your organization, in the order of last created.

     * **key** - the unique key of this field (string), filterable as `key`
     * **label** - the display label of this field (string)
     * **value_type** - the data type of values associated with this field (string)

    Example:

        GET /api/v3/fields.json

    Response containing the fields for your organization:

         {
            "next": null,
            "previous": null,
            "results": [
                {
                    "key": "nick_name",
                    "label": "Nick name",
                    "value_type": "text"
                },
                ...
            ]
        }

    ## Adding Fields

    A **POST** can be used to create a new contact field. Don't specify a key as this will be generated for you.

    * **label** - the display label (string)
    * **value_type** - one of the value type codes (string)

    Example:

        POST /api/v3/fields.json
        {
            "label": "Nick name",
            "value_type": "text"
        }

    You will receive a field object (with the new field key) as a response if successful:

        {
            "key": "nick_name",
            "label": "Nick name",
            "value_type": "text"
        }

    ## Updating Fields

    A **POST** can also be used to update an existing field if you include it's key in the URL.

    Example:

        POST /api/v3/fields.json?key=nick_name
        {
            "label": "New label",
            "value_type": "text"
        }

    You will receive the updated field object as a response if successful:

        {
            "key": "nick_name",
            "label": "New label",
            "value_type": "text"
        }
    """
    @classmethod
    def get_read_explorer(cls):
        source_object = FieldsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.fields')
        return source_object

    @classmethod
    def get_write_explorer(cls):
        source_object = FieldsEndpointV2.get_write_explorer()
        source_object['url'] = reverse('api.v3.fields')
        return source_object


class FlowsEndpoint(FlowsEndpointV2):
    """
    This endpoint allows you to list flows in your account.

    ## Listing Flows

    A **GET** returns the list of flows for your organization, in the order of last created.

     * **uuid** - the UUID of the flow (string), filterable as `uuid`
     * **name** - the name of the flow (string)
     * **archived** - whether this flow is archived (boolean)
     * **labels** - the labels for this flow (array of objects)
     * **expires** - the time (in minutes) when this flow's inactive contacts will expire (integer)
     * **created_on** - when this flow was created (datetime)
     * **modified_on** - when this flow was last modified (datetime), filterable as `before` and `after`.
     * **runs** - the counts of completed, interrupted and expired runs (object)
     * **revision** - the number of the flow's revision (integer)
     * **launch_status** - launch status for surveyor flows, it can be "D" (Demo) or "P" (Production) (string)

    Example:

        GET /api/v3/flows.json

    Response containing the flows for your organization:

        {
            "next": null,
            "previous": null,
            "results": [
                {
                    "uuid": "5f05311e-8f81-4a67-a5b5-1501b6d6496a",
                    "name": "Survey",
                    "archived": false,
                    "labels": [{"name": "Important", "uuid": "5a4eb79e-1b1f-4ae3-8700-09384cca385f"}],
                    "expires": 600,
                    "created_on": "2016-01-06T15:33:00.813162Z",
                    "modified_on": "2017-01-07T13:14:00.453567Z",
                    "runs": {
                        "active": 47,
                        "completed": 123,
                        "interrupted": 2,
                        "expired": 34
                    },
                    "revision": 1,
                    "launch_status": "P"
                },
                ...
            ]
        }
    """
    serializer_class = FlowReadSerializer

    @classmethod
    def get_read_explorer(cls):
        source_object = FlowsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.flows')
        return source_object

    def filter_queryset(self, queryset):
        params = self.request.query_params

        queryset = queryset.exclude(flow_type=Flow.MESSAGE).filter(is_active=True)

        # filter by UUID (optional)
        uuid = params.get('uuid')
        if uuid:
            queryset = queryset.filter(uuid=uuid)

        archived = params.get('archived')
        if archived is not None:
            queryset = queryset.filter(is_archived=str_to_bool(archived))

        flow_type = params.get('type')
        if flow_type:  # pragma: needs cover
            queryset = queryset.filter(flow_type__in=flow_type)

            # If the flow is survey, we'll apply a filter to show only launched flows for non-admin users
            if flow_type == Flow.SURVEY:
                user_org = self.request.user.get_org()

                # if user is not an administrator
                if user_org.id not in self.request.user.org_admins.filter(is_active=True).only('id').values_list('id', flat=True):
                    queryset = queryset.filter(launch_status=Flow.STATUS_PRODUCTION)

        queryset = queryset.prefetch_related('labels')

        return self.filter_before_after(queryset, 'modified_on')


class FlowStartsEndpoint(FlowStartsEndpointV2):
    """
    This endpoint allows you to list manual flow starts in your account, and add or start contacts in a flow.

    ## Listing Flow Starts

    By making a `GET` request you can list all the manual flow starts on your organization, in the order of last
    modified. Each flow start has the following attributes:

     * **uuid** - the UUID of this flow start (string)
     * **flow** - the flow which was started (object)
     * **contacts** - the list of contacts that were started in the flow (objects)
     * **groups** - the list of groups that were started in the flow (objects)
     * **restart_particpants** - whether the contacts were restarted in this flow (boolean)
     * **status** - the status of this flow start
     * **extra** - the dictionary of extra parameters passed to the flow start (object)
     * **created_on** - the datetime when this flow start was created (datetime)
     * **modified_on** - the datetime when this flow start was modified (datetime)

    Example:

        GET /api/v3/flow_starts.json

    Response is the list of flow starts on your organization, most recently modified first:

        {
            "next": "http://example.com/api/v2/flow_starts.json?cursor=cD0yMDE1LTExLTExKzExJTNBM40NjQlMkIwMCUzRv",
            "previous": null,
            "results": [
                {
                    "uuid": "09d23a05-47fe-11e4-bfe9-b8f6b119e9ab",
                    "flow": {"uuid": "f5901b62-ba76-4003-9c62-72fdacc1b7b7", "name": "Thrift Shop"},
                    "groups": [
                         {"uuid": "f5901b62-ba76-4003-9c62-72fdacc1b7b7", "name": "Ryan & Macklemore"}
                    ],
                    "contacts": [
                         {"uuid": "f5901b62-ba76-4003-9c62-fjjajdsi15553", "name": "Wanz"}
                    ],
                    "restart_participants": true,
                    "status": "complete",
                    "extra": {
                        "first_name": "Ryan",
                        "last_name": "Lewis"
                    },
                    "created_on": "2013-08-19T19:11:21.082Z",
                    "modified_on": "2013-08-19T19:11:21.082Z"
                },
                ...
            ]
        }

    ## Starting contacts down a flow

    By making a `POST` request with the contacts, groups and URNs you want to start down a flow you can trigger a flow
    start. Note that that contacts will be added to the flow asynchronously, you can use the runs endpoint to monitor the
    runs created by this start.

     * **flow** - the UUID of the flow to start contacts in (required)
     * **groups** - the UUIDs of the groups you want to start in this flow (array of up to 100 strings, optional)
     * **contacts** - the UUIDs of the contacts you want to start in this flow (array of up to 100 strings, optional)
     * **urns** - the URNs you want to start in this flow (array of up to 100 strings, optional)
     * **restart_participants** - whether to restart participants already in this flow (optional, defaults to true)
     * **extra** - a dictionary of extra parameters to pass to the flow start (accessible via @extra in your flow)

    Example:

        POST /api/v3/flow_starts.json
        {
            "flow": "f5901b62-ba76-4003-9c62-72fdacc1b7b7",
            "groups": ["f5901b62-ba76-4003-9c62-72fdacc15515"],
            "contacts": ["f5901b62-ba76-4003-9c62-fjjajdsi15553"],
            "urns": ["twitter:sirmixalot", "tel:+12065551212"],
            "extra": {"first_name": "Ryan", "last_name": "Lewis"}
        }

    Response is the created flow start:

        {
            "uuid": "09d23a05-47fe-11e4-bfe9-b8f6b119e9ab",
            "flow": {"uuid": "f5901b62-ba76-4003-9c62-72fdacc1b7b7", "name": "Thrift Shop"},
            "groups": [
                 {"uuid": "f5901b62-ba76-4003-9c62-72fdacc1b7b7", "name": "Ryan & Macklemore"}
            ],
            "contacts": [
                 {"uuid": "f5901b62-ba76-4003-9c62-fjjajdsi15553", "name": "Wanz"}
            ],
            "restart_participants": true,
            "status": "complete",
            "extra": {
                "first_name": "Ryan",
                "last_name": "Lewis"
            },
            "created_on": "2013-08-19T19:11:21.082Z",
            "modified_on": "2013-08-19T19:11:21.082Z"
        }

    """
    @classmethod
    def get_read_explorer(cls):
        source_object = FlowStartsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.flow_starts')
        return source_object

    @classmethod
    def get_write_explorer(cls):
        source_object = FlowStartsEndpointV2.get_write_explorer()
        source_object['url'] = reverse('api.v3.flow_starts')
        return source_object


class FlowStepEndpoint(FlowStepEndpointV1):
    """
    This endpoint allows you to create flow runs and steps.

    ## Creating flow steps

    By making a ```POST``` request to the endpoint you can add a new steps to a flow run.

    * **flow** - the UUID of the flow (string)
    * **revision** - the revision of the flow that was executed (integer)
    * **contact** - the UUID of the contact (string)
    * **steps** - the new step objects (array of objects)
    * **started** - the datetime when the run was started
    * **completed** - whether the run is complete

    Example:

        POST /api/v3/steps.json
        {
            "flow": "f5901b62-ba76-4003-9c62-72fdacc1b7b7",
            "revision": 2,
            "contact": "cf85cb74-a4e4-455b-9544-99e5d9125cfd",
            "completed": true,
            "started": "2015-09-23T17:59:47.572Z"
            "steps": [
                {
                    "node": "32cf414b-35e3-4c75-8a78-d5f4de925e13",
                    "arrived_on": "2015-08-25T11:59:30.088Z",
                    "actions": [{"msg":"Hi Joe","type":"reply"}],
                    "errors": []
                }
            ]
        }

    Response is the updated or created flow run.
    """
    permission = 'flows.flow_api'
    write_serializer_class = FlowRunWriteSerializer

    @classmethod
    def get_write_explorer(cls):
        return {
            'method': "POST",
            'title': "Create or update a flow run with new steps",
            'url': reverse('api.v3.steps'),
            'slug': 'step-post',
            'fields': [dict(name='contact', required=True,
                            help="The UUID of the contact"),
                       dict(name='flow', required=True,
                            help="The UUID of the flow"),
                       dict(name='started', required=True,
                            help='Datetime when the flow started'),
                       dict(name='completed', required=True,
                            help='Boolean whether the run is complete or not'),
                       dict(name='steps', required=True,
                            help="A JSON array of one or objects, each a flow step")],
            'example': {'body': '{ "contact": "cf85cb74-a4e4-455b-9544-99e5d9125cfd", "flow": "f5901b62-ba76-4003-9c62-72fdacc1b7b7", "steps": [{"node": "32cf414b-35e3-4c75-8a78-d5f4de925e13", "arrived_on": "2015-08-25T11:59:30.088Z", "actions": [{"msg":"Hi Joe","type":"reply"}], "errors": []}] }'},
        }


class GroupsEndpoint(GroupsEndpointV2):
    """
    This endpoint allows you to list, create, update and delete contact groups in your account.

    ## Listing Groups

    A **GET** returns the list of contact groups for your organization, in the order of last created.

     * **uuid** - the UUID of the group (string), filterable as `uuid`
     * **name** - the name of the group (string), filterable as `name`
     * **count** - the number of contacts in the group (int)

    Example:

        GET /api/v3/groups.json

    Response containing the groups for your organization:

        {
            "next": null,
            "previous": null,
            "results": [
                {
                    "uuid": "5f05311e-8f81-4a67-a5b5-1501b6d6496a",
                    "name": "Reporters",
                    "count": 315,
                    "query": null
                },
                ...
            ]
        }

    ## Adding a Group

    A **POST** can be used to create a new contact group. Don't specify a UUID as this will be generated for you.

    * **name** - the group name (string)

    Example:

        POST /api/v3/groups.json
        {
            "name": "Reporters"
        }

    You will receive a group object as a response if successful:

        {
            "uuid": "5f05311e-8f81-4a67-a5b5-1501b6d6496a",
            "name": "Reporters",
            "count": 0,
            "query": null
        }

    ## Updating a Group

    A **POST** can also be used to update an existing contact group if you specify its UUID in the URL.

    Example:

        POST /api/v3/groups.json?uuid=5f05311e-8f81-4a67-a5b5-1501b6d6496a
        {
            "name": "Checked"
        }

    You will receive the updated group object as a response if successful:

        {
            "uuid": "5f05311e-8f81-4a67-a5b5-1501b6d6496a",
            "name": "Checked",
            "count": 0,
            "query": null
        }

    ## Deleting a Group

    A **DELETE** can be used to delete a contact group if you specify its UUID in the URL.

    Example:

        DELETE /api/v3/groups.json?uuid=5f05311e-8f81-4a67-a5b5-1501b6d6496a

    You will receive either a 204 response if a group was deleted, or a 404 response if no matching group was found.
    """
    @classmethod
    def get_read_explorer(cls):
        source_object = GroupsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.groups')
        return source_object

    @classmethod
    def get_write_explorer(cls):
        source_object = GroupsEndpointV2.get_write_explorer()
        source_object['url'] = reverse('api.v3.groups')
        return source_object

    @classmethod
    def get_delete_explorer(cls):
        source_object = GroupsEndpointV2.get_delete_explorer()
        source_object['url'] = reverse('api.v3.groups')
        return source_object


class LabelsEndpoint(LabelsEndpointV2):
    """
    This endpoint allows you to list, create, update and delete message labels in your account.

    ## Listing Labels

    A **GET** returns the list of message labels for your organization, in the order of last created.

     * **uuid** - the UUID of the label (string), filterable as `uuid`
     * **name** - the name of the label (string), filterable as `name`
     * **count** - the number of messages with this label (int)

    Example:

        GET /api/v3/labels.json

    Response containing the labels for your organization:

        {
            "next": null,
            "previous": null,
            "results": [
                {
                    "uuid": "5f05311e-8f81-4a67-a5b5-1501b6d6496a",
                    "name": "Screened",
                    "count": 315
                },
                ...
            ]
        }

    ## Adding a Label

    A **POST** can be used to create a new message label. Don't specify a UUID as this will be generated for you.

    * **name** - the label name (string)

    Example:

        POST /api/v3/labels.json
        {
            "name": "Screened"
        }

    You will receive a label object as a response if successful:

        {
            "uuid": "fdd156ca-233a-48c1-896d-a9d594d59b95",
            "name": "Screened",
            "count": 0
        }

    ## Updating a Label

    A **POST** can also be used to update an existing message label if you specify its UUID in the URL.

    Example:

        POST /api/v3/labels.json?uuid=fdd156ca-233a-48c1-896d-a9d594d59b95
        {
            "name": "Checked"
        }

    You will receive the updated label object as a response if successful:

        {
            "uuid": "fdd156ca-233a-48c1-896d-a9d594d59b95",
            "name": "Checked",
            "count": 0
        }

    ## Deleting a Label

    A **DELETE** can be used to delete a message label if you specify its UUID in the URL.

    Example:

        DELETE /api/v3/labels.json?uuid=fdd156ca-233a-48c1-896d-a9d594d59b95

    You will receive either a 204 response if a label was deleted, or a 404 response if no matching label was found.
    """
    @classmethod
    def get_read_explorer(cls):
        source_object = LabelsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.labels')
        return source_object

    @classmethod
    def get_write_explorer(cls):
        source_object = LabelsEndpointV2.get_write_explorer()
        source_object['url'] = reverse('api.v3.labels')
        return source_object

    @classmethod
    def get_delete_explorer(cls):
        source_object = LabelsEndpointV2.get_delete_explorer()
        source_object['url'] = reverse('api.v3.labels')
        return source_object


class MediaEndpoint(MediaEndpointV2):
    """
    This endpoint allows you to submit media which can be embedded in flow steps.

    ## Creating Media

    By making a `POST` request to the endpoint you can add a new media files

    * **media_file** - the file to upload
    * **extension** - the extension of the file

    Example:

        curl --request POST \\
             --url http://example.com/api/v3/media.json \\
             --header 'authorization: Token your-token-here' \\
             --form media_file=file.png \\
             --form extension=png
    """


class MessagesEndpoint(MessagesEndpointV2):
    """
    This endpoint allows you to list messages in your account.

    ## Listing Messages

    A `GET` returns the messages for your organization, filtering them as needed. Each message has the following
    attributes:

     * **id** - the ID of the message (int), filterable as `id`.
     * **broadcast** - the id of the broadcast (int), filterable as `broadcast`.
     * **contact** - the UUID and name of the contact (object), filterable as `contact` with UUID.
     * **urn** - the URN of the sender or receiver, depending on direction (string).
     * **channel** - the UUID and name of the channel that handled this message (object).
     * **direction** - the direction of the message (one of "incoming" or "outgoing").
     * **type** - the type of the message (one of "inbox", "flow", "ivr").
     * **status** - the status of the message (one of "initializing", "queued", "wired", "sent", "delivered", "handled", "errored", "failed", "resent").
     * **media** - the media if set for a message (ie, the recording played for IVR messages, audio-xwav:http://domain.com/recording.wav)
     * **visibility** - the visibility of the message (one of "visible", "archived" or "deleted")
     * **text** - the text of the message received (string). Note this is the logical view and the message may have been received as multiple physical messages.
     * **labels** - any labels set on this message (array of objects), filterable as `label` with label name or UUID.
     * **created_on** - when this message was either received by the channel or created (datetime) (filterable as `before` and `after`).
     * **sent_on** - for outgoing messages, when the channel sent the message (null if not yet sent or an incoming message) (datetime).

    You can also filter by `folder` where folder is one of `inbox`, `flows`, `archived`, `outbox`, `incoming` or `sent`.
    Note that you cannot filter by more than one of `contact`, `folder`, `label` or `broadcast` at the same time.

    The sort order for all folders save for `incoming` is the message creation date. For the `incoming` folder (which
    includes all incoming messages, regardless of visibility or type) messages are sorted by last modified date. This
    allows clients to poll for updates to message labels and visibility changes.

    Example:

        GET /api/v3/messages.json?folder=inbox

    Response is the list of messages for that contact, most recently created first:

        {
            "next": "http://example.com/api/v3/messages.json?folder=inbox&cursor=cD0yMDE1LTExLTExKzExJTNBM40NjQlMkIwMCUzRv",
            "previous": null,
            "results": [
            {
                "id": 4105426,
                "broadcast": 2690007,
                "contact": {"uuid": "d33e9ad5-5c35-414c-abd4-e7451c69ff1d", "name": "Bob McFlow"},
                "urn": "twitter:textitin",
                "channel": {"uuid": "9a8b001e-a913-486c-80f4-1356e23f582e", "name": "Nexmo"},
                "direction": "out",
                "type": "inbox",
                "status": "wired",
                "visibility": "visible",
                "text": "How are you?",
                "media": "wav:http://domain.com/recording.wav",
                "labels": [{"name": "Important", "uuid": "5a4eb79e-1b1f-4ae3-8700-09384cca385f"}],
                "created_on": "2016-01-06T15:33:00.813162Z",
                "sent_on": "2016-01-06T15:35:03.675716Z"
            },
            ...
        }
    """
    throttle_scope = 'v3.messages'

    @classmethod
    def get_read_explorer(cls):
        source_object = MessagesEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.messages')
        return source_object


class MessageActionsEndpoint(MessageActionsEndpointV2):
    """
    ## Bulk Message Updating

    A **POST** can be used to perform an action on a set of messages in bulk.

    * **messages** - the message ids (array of up to 100 integers)
    * **action** - the action to perform, a string one of:

        * _label_ - Apply the given label to the messages
        * _unlabel_ - Remove the given label from the messages
        * _archive_ - Archive the messages
        * _restore_ - Restore the messages if they are archived
        * _delete_ - Permanently delete the messages

    * **label** - the UUID or name of an existing label (string, optional)
    * **label_name** - the name of a label which can be created if it doesn't exist (string, optional)

    If labelling or unlabelling messages using `label` you will get an error response (400) if the label doesn't exist.
    If labelling with `label_name` the label will be created if it doesn't exist, and if unlabelling it is ignored if
    it doesn't exist.

    Example:

        POST /api/v3/message_actions.json
        {
            "messages": [1234, 2345, 3456],
            "action": "label",
            "label": "Testing"
        }

    You will receive an empty response with status code 204 if successful.
    """
    @classmethod
    def get_write_explorer(cls):
        source_object = MessageActionsEndpointV2.get_write_explorer()
        source_object['url'] = reverse('api.v3.message_actions')
        return source_object


class OrgEndpoint(OrgEndpointV2):
    """
    This endpoint allows you to view details about your account.

    ## Viewing Current Organization

    A **GET** returns the details of your organization. There are no parameters.

    Example:

        GET /api/v3/org.json

    Response containing your organization:

        {
            "name": "Nyaruka",
            "country": "RW",
            "languages": ["eng", "fre"],
            "primary_language": "eng",
            "timezone": "Africa/Kigali",
            "date_style": "day_first",
            "credits": {"used": 121433, "remaining": 3452},
            "anon": false
        }
    """
    @classmethod
    def get_read_explorer(cls):
        source_object = OrgEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.org')
        return source_object


class ResthooksEndpoint(ResthooksEndpointV2):
    """
    This endpoint allows you to list configured resthooks in your account.

    ## Listing Resthooks

    A `GET` returns the resthooks on your organization. Each resthook has the following attributes:

     * **resthook** - the slug for the resthook (string)
     * **created_on** - the datetime when this resthook was created (datetime)
     * **modified_on** - the datetime when this resthook was last modified (datetime)

    Example:

        GET /api/v3/resthooks.json

    Response is the list of resthooks on your organization, most recently modified first:

        {
            "next": "http://example.com/api/v3/resthooks.json?cursor=cD0yMDE1LTExLTExKzExJTNBM40NjQlMkIwMCUzRv",
            "previous": null,
            "results": [
            {
                "resthook": "new-report",
                "created_on": "2015-11-11T13:05:57.457742Z",
                "modified_on": "2015-11-11T13:05:57.457742Z",
            },
            ...
        }
    """
    @classmethod
    def get_read_explorer(cls):
        source_object = ResthooksEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.resthooks')
        return source_object


class ResthookEventsEndpoint(ResthookEventsEndpointV2):
    """
    This endpoint lists recent events for the passed in Resthook.

    ## Listing Resthook Events

    A `GET` returns the recent resthook events on your organization. Each event has the following attributes:

     * **resthook** - the slug for the resthook (filterable)
     * **data** - the data for the resthook
     * **created_on** - the datetime when this resthook was created (datetime)

    Example:

        GET /api/v3/resthook_events.json

    Response is the list of recent resthook events on your organization, most recently created first:

        {
            "next": "http://example.com/api/v3/resthook_events.json?cursor=cD0yMDE1LTExLTExKzExJTNBM40NjQlMkIwMCUzRv",
            "previous": null,
            "results": [
            {
                "resthook": "new-report",
                "data": {
                    "channel": 105,
                    "flow": 50505,
                    "flow_base_language": "eng",
                    "run": 50040405,
                    "text": "Incoming text",
                    "step: "d33e9ad5-5c35-414c-abd4-e7451c69ff1d",
                    "contact": "d33e9ad5-5c35-414c-abd4-e7451casdf",
                    "urn": "tel:+12067781234",
                    "values": [
                        {
                            "category": {
                                "eng": "All Responses"
                            },
                            "node": "c33724d7-1064-4dd6-9aa3-efd29252cb88",
                            "text": "Ryan Lewis",
                            "rule_value": "Ryan Lewis",
                            "value": "Ryan Lewis",
                            "label": "Name",
                            "time": "2016-08-10T21:18:51.186826Z"
                        }
                    ],
                    "steps": [
                        {
                            "node": "2d4f8c9a-cf12-4f6c-ad55-a6cc633954f6",
                            "left_on": "2016-08-10T21:18:45.391114Z",
                            "text": "What is your name?",
                            "value": null,
                            "arrived_on": "2016-08-10T21:18:45.378598Z",
                            "type": "A"
                        },
                        {
                            "node": "c33724d7-1064-4dd6-9aa3-efd29252cb88",
                            "left_on": "2016-08-10T21:18:51.186826Z",
                            "text": "Eric Newcomer",
                            "value": "Eric Newcomer",
                            "arrived_on": "2016-08-10T21:18:45.391114Z",
                            "type": "R"
                        }
                    ],
                },
                "created_on": "2015-11-11T13:05:57.457742Z",
            },
            ...
        }
    """
    @classmethod
    def get_read_explorer(cls):
        source_object = ResthookEventsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.resthook_events')
        return source_object


class ResthookSubscribersEndpoint(ResthookSubscribersEndpointV2):
    """
    This endpoint allows you to list, add or remove subscribers to resthooks.

    ## Listing Resthook Subscribers

    A `GET` returns the subscribers on your organization. Each resthook subscriber has the following attributes:

     * **id** - the id of the subscriber (integer, filterable)
     * **resthook** - the resthook they are subscribed to (string, filterable)
     * **target_url** - the url that will be notified when this event occurs
     * **created_on** - when this subscriber was added

    Example:

        GET /api/v3/resthook_subscribers.json

    Response is the list of resthook subscribers on your organization, most recently created first:

        {
            "next": "http://example.com/api/v3/resthook_subscribers.json?cursor=cD0yMDE1LTExLTExKzExJTNBM40NjQlMkIwMCUzRv",
            "previous": null,
            "results": [
            {
                "id": "10404016"
                "resthook": "mother-registration",
                "target_url": "https://zapier.com/receive/505019595",
                "created_on": "2013-08-19T19:11:21.082Z"
            },
            {
                "id": "10404055",
                "resthook": "new-birth",
                "target_url": "https://zapier.com/receive/605010501",
                "created_on": "2013-08-19T19:11:21.082Z"
            },
            ...
        }

    ## Subscribing to a Resthook

    By making a `POST` request with the event you want to subscribe to and the target URL, you can subscribe to be
    notified whenever your resthook event is triggered.

     * **resthook** - the slug of the resthook to subscribe to
     * **target_url** - the URL you want called (will be called with a POST)

    Example:

        POST /api/v3/resthook_subscribers.json
        {
            "resthook": "new-report",
            "target_url": "https://zapier.com/receive/505019595"
        }

    Response is the created subscription:

        {
            "id": "10404016",
            "resthook": "new-report",
            "target_url": "https://zapier.com/receive/505019595",
            "created_on": "2013-08-19T19:11:21.082Z"
        }

    ## Deleting a Subscription

    A **DELETE** can be used to delete a subscription if you specify its id in the URL.

    Example:

        DELETE /api/v3/resthook_subscribers.json?id=10404016

    You will receive either a 204 response if a subscriber was deleted, or a 404 response if no matching subscriber was found.

    """
    @classmethod
    def get_read_explorer(cls):
        source_object = ResthookSubscribersEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.resthook_subscribers')
        return source_object

    @classmethod
    def get_write_explorer(cls):
        source_object = ResthookSubscribersEndpointV2.get_write_explorer()
        source_object['url'] = reverse('api.v3.resthook_subscribers')
        return source_object

    @classmethod
    def get_delete_explorer(cls):
        source_object = ResthookSubscribersEndpointV2.get_delete_explorer()
        source_object['url'] = reverse('api.v3.resthook_subscribers')
        return source_object


class RunsEndpoint(RunsEndpointV2):
    """
    This endpoint allows you to fetch flow runs. A run represents a single contact's path through a flow and is created
    each time a contact is started in a flow.

    ## Listing Flow Runs

    A `GET` request returns the flow runs for your organization, filtering them as needed. Each
    run has the following attributes:

     * **id** - the ID of the run (int), filterable as `id`.
     * **flow** - the UUID and name of the flow (object), filterable as `flow` with UUID.
     * **contact** - the UUID and name of the contact (object), filterable as `contact` with UUID.
     * **submitted_by** - the first name and last name of the user that submitted (object), filterable as `submitted_by`.
     * **responded** - whether the contact responded (boolean), filterable as `responded`.
     * **path** - the contact's path through the flow nodes (array of objects)
     * **values** - values generated by rulesets in the flow (array of objects).
     * **created_on** - the datetime when this run was started (datetime).
     * **modified_on** - when this run was last modified (datetime), filterable as `before` and `after`.
     * **exited_on** - the datetime when this run exited or null if it is still active (datetime).
     * **exit_type** - how the run ended (one of "interrupted", "completed", "expired").

    Note that you cannot filter by `flow` and `contact` at the same time.

    Example:

        GET /api/v3/runs.json?flow=f5901b62-ba76-4003-9c62-72fdacc1b7b7

    Response is the list of runs on the flow, most recently modified first:

        {
            "next": "http://example.com/api/v3/runs.json?cursor=cD0yMDE1LTExLTExKzExJTNBM40NjQlMkIwMCUzRv",
            "previous": null,
            "results": [
            {
                "id": 12345678,
                "flow": {"uuid": "f5901b62-ba76-4003-9c62-72fdacc1b7b7", "name": "Favorite Color"},
                "contact": {"uuid": "d33e9ad5-5c35-414c-abd4-e7451c69ff1d", "name": "Bob McFlow"},
                "responded": true,
                "path": [
                    {"node": "27a86a1b-6cc4-4ae3-b73d-89650966a82f", "time": "2015-11-11T13:05:50.457742Z"},
                    {"node": "fc32aeb0-ac3e-42a8-9ea7-10248fdf52a1", "time": "2015-11-11T13:03:51.635662Z"},
                    {"node": "93a624ad-5440-415e-b49f-17bf42754acb", "time": "2015-11-11T13:03:52.532151Z"},
                    {"node": "4c9cb68d-474f-4b9a-b65e-c2aa593a3466", "time": "2015-11-11T13:05:57.576056Z"}
                ],
                "values": {
                    "color": {
                        "value": "blue",
                        "category": "Blue",
                        "node": "fc32aeb0-ac3e-42a8-9ea7-10248fdf52a1",
                        "time": "2015-11-11T13:03:51.635662Z"
                    },
                    "reason": {
                        "value": "Because it's the color of sky",
                        "category": "All Responses",
                        "node": "4c9cb68d-474f-4b9a-b65e-c2aa593a3466",
                        "time": "2015-11-11T13:05:57.576056Z"
                    }
                },
                "created_on": "2015-11-11T13:05:57.457742Z",
                "modified_on": "2015-11-11T13:05:57.576056Z",
                "exited_on": "2015-11-11T13:05:57.576056Z",
                "exit_type": "completed"
            },
            ...
        }
    """
    throttle_scope = 'v3.runs'
    serializer_class = FlowRunReadSerializer

    def filter_queryset(self, queryset):
        params = self.request.query_params
        org = self.request.user.get_org()

        # filter by flow (optional)
        flow_uuid = params.get('flow')
        if flow_uuid:
            flow = Flow.objects.filter(org=org, uuid=flow_uuid, is_active=True).first()
            if flow:
                queryset = queryset.filter(flow=flow)
            else:
                queryset = queryset.filter(pk=-1)

        # filter by id (optional)
        run_id = self.get_int_param('id')
        if run_id:
            queryset = queryset.filter(id=run_id)

        # filter by submitted_by (optional)
        submitted_by = self.get_int_param('submitted_by')
        if submitted_by:
            queryset = queryset.filter(submitted_by=submitted_by)

        # filter by contact (optional)
        contact_uuid = params.get('contact')
        if contact_uuid:
            contact = Contact.objects.filter(org=org, is_test=False, is_active=True, uuid=contact_uuid).first()
            if contact:
                queryset = queryset.filter(contact=contact)
            else:
                queryset = queryset.filter(pk=-1)
        else:
            # otherwise filter out test contact runs
            test_contact_ids = list(Contact.objects.filter(org=org, is_test=True).values_list('pk', flat=True))
            queryset = queryset.exclude(contact__pk__in=test_contact_ids)

        # limit to responded runs (optional)
        if str_to_bool(params.get('responded')):
            queryset = queryset.filter(responded=True)

        # use prefetch rather than select_related for foreign keys to avoid joins
        queryset = queryset.prefetch_related(
            Prefetch('flow', queryset=Flow.objects.only('uuid', 'name', 'base_language')),
            Prefetch('contact', queryset=Contact.objects.only('uuid', 'name', 'language')),
            Prefetch('start', queryset=FlowStart.objects.only('uuid')),
            Prefetch('values'),
            Prefetch('values__ruleset', queryset=RuleSet.objects.only('uuid', 'label')),
            Prefetch('steps', queryset=FlowStep.objects.only('run', 'step_uuid', 'arrived_on').order_by('arrived_on'))
        )

        return self.filter_before_after(queryset, 'modified_on')

    @classmethod
    def get_read_explorer(cls):
        source_object = RunsEndpointV2.get_read_explorer()
        source_object['url'] = reverse('api.v3.runs')
        return source_object


# Surveyor views

class MeEndpoint(BaseAPIView):
    """
    This endpoint allows you to view details about the user logged.

    ## Viewing Current User

    A **GET** returns the details of the user logged. There are no parameters.

    The role field could be "Administrators", "Editors", "Viewers" and "Surveyors"

    Example:

        GET /api/v3/me.json

    Response containing your organization:

        {
            "id": 1,
            "full_name": "John Connor",
            "first_name": "John",
            "last_name": "Connor",
            "email": "johnconnor@example.com",
            "role": "Administrators"
        }

    ## Updating User

    A **POST** request will update the first name and last name of the user.

    Example:

        POST /api/v3/me.json

    Response containing your organization:

        {
            "first_name": "John",
            "last_name": "Connor"
        }

    """
    permission = 'orgs.org_api'

    def post(self, request, *args, **kwargs):
        body = request.data
        user = request.user

        first_name = body.get('first_name', None)
        last_name = body.get('last_name', None)

        errors = []

        if first_name:
            user.first_name = first_name
        else:
            errors.append(dict(field='first_name', message=_('This field is required')))

        if last_name:
            user.last_name = last_name
        else:
            errors.append(dict(field='last_name', message=_('This field is required')))

        if not errors or first_name or last_name:
            user.save(update_fields=['first_name', 'last_name'])
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        else:
            return JsonResponse({'errors': errors}, safe=False, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
        user = request.user

        api_token = get_apitoken_from_auth(user.api_token)
        org = api_token.org if api_token else None
        if not org or not org.is_active or org.is_suspended():
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

        role = org.get_user_org_group(user)
        data = {
            'id': user.id,
            'full_name': user.get_full_name(),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': role.name
        }

        return Response(data, status=status.HTTP_200_OK)

    @classmethod
    def get_write_explorer(cls):
        return {
            'method': "POST",
            'title': "Action to update first name and last name of the user",
            'url': reverse('api.v3.me'),
            'slug': 'me-write',
            'fields': [dict(name='first_name', required=True,
                            help="The first name of the user"),
                       dict(name='last_name', required=True,
                            help="The last name of the user")],
            'example': {'body': '{"first_name": "John", "last_name": "Connor"}'},
        }

    @classmethod
    def get_read_explorer(cls):
        return {
            'method': "GET",
            'title': "View Current User",
            'url': reverse('api.v3.me'),
            'slug': 'me-read'
        }


class UserOrgsEndpoint(BaseAPIView, ListAPIMixin):
    """
    Provides the user's organizations and API tokens to use on Surveyor App
    """

    permission = 'orgs.org_api'

    def list(self, request, *args, **kwargs):
        user = request.user
        user_orgs = get_user_orgs(user)
        orgs = []

        for org in user_orgs:
            user_group = org.get_user_org_group(user)
            token = APIToken.get_or_create(org, user, user_group)
            orgs.append({'org': {'id': org.pk, 'name': org.name}, 'token': token.key})

        return JsonResponse(orgs, safe=False, json_dumps_params={'indent': 2})

    @classmethod
    def get_read_explorer(cls):
        return {
            'method': "GET",
            'title': "Provides the user's organizations and API tokens to use on Surveyor App",
            'url': reverse('api.v3.user_orgs'),
            'slug': 'user-orgs',
            'custom_docs': '%s#user-orgs' % reverse('api.v3.custom_endpoints')
        }


class ManageAccountsListEndpoint(BaseAPIView, ListAPIMixin):
    """
    Provides the users that are pending of approbation
    """

    permission = 'orgs.org_manage_accounts'

    def list(self, request, *args, **kwargs):
        user = request.user

        api_token = get_apitoken_from_auth(user.api_token)
        org = api_token.org if api_token else None

        if not org:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

        surveryors = org.surveyors.filter(is_active=False).order_by('username')
        users = []

        role = APIToken.get_role_from_code('S')

        if role:
            for user in surveryors:
                users.append({'username': user.username, 'id': user.id})

        else:  # pragma: needs cover
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)

        return JsonResponse(users, safe=False, json_dumps_params={'indent': 2})

    @classmethod
    def get_read_explorer(cls):
        return {
            'method': "GET",
            'title': "Provides the users that are pending of approbation",
            'url': reverse('api.v3.manage_accounts_list'),
            'slug': 'manage-accounts-list',
            'custom_docs': '%s#manage-accounts' % reverse('api.v3.custom_endpoints')
        }


class ManageAccountsActionEndpoint(BaseAPIView, WriteAPIMixin):
    """
    ## Action to approve or deny users

    A **POST** can be used to perform an action to approve or deny users.

    * **id** - the user id

    Example:

        POST /api/v3/manage-accounts/action/(approve|deny).json

        [
            {
                "id": 1
            },
            {
                "id": 2
            },
            {
                "id": 3
            }
        ]

    You will receive an empty response with status code 204 if successful.

    """

    permission = 'orgs.org_manage_accounts'

    def post(self, request, *args, **kwargs):
        body = request.data
        action = kwargs.get('action')

        errors = []

        for item in body:
            user = User.objects.filter(id=int(item.get('id'))).first()
            if user and not user.is_active:
                user_email = user.email
                if action == 'approve':
                    user.is_active = True
                    user.save(update_fields=['is_active'])
                    message = _('Congrats! Your account is approved. Please log in to access your surveys.')
                else:
                    user.delete()
                    message = _('Sorry. Your account was not approved. If you think this was a mistake, '
                                'please contact %s.' % request.user.email)

                send_account_manage_email_task.delay(user_email, message)
            else:
                errors.append(_('User ID %s not found or already is active' % item.get('id')))

        if errors:
            return JsonResponse({'errors': errors}, safe=False, status=status.HTTP_400_BAD_REQUEST,
                                json_dumps_params={'indent': 2})
        else:
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    @classmethod
    def get_approve_write_explorer(cls):
        return {
            'method': "POST",
            'title': "Action to approve users",
            'url': reverse('api.v3.manage_accounts_action', args=['approve']),
            'slug': 'manage-accounts-action-approve',
            'fields': [dict(name='id', required=True,
                            help="The ID of the user")],
            'example': {'body': '[{"id": 1}]'},
        }

    @classmethod
    def get_deny_write_explorer(cls):
        return {
            'method': "POST",
            'title': "Action to deny users",
            'url': reverse('api.v3.manage_accounts_action', args=['deny']),
            'slug': 'manage-accounts-action-deny',
            'fields': [dict(name='id', required=True,
                            help="The ID of the user")],
            'example': {'body': '[{"id": 1}]'},
        }


class DeviceTokenEndpoint(BaseAPIView, WriteAPIMixin):
    """
    ## Action to add device token to user

    A **POST** can be used to perform an action to add device token users.

    * **device_token** - the user device token

    Example:

        POST /api/v3/user/device_token.json
        {
            "device_token": "15MsMdEICogXSLB8-MrdkRuRQFwNI5u8Dh0cI90ABD3BOKnxkEla8cGdisbDHl5cVIkZah5QUhSAxzx4Roa7b4xy9tvx9iNSYw"
        }

    You will receive an empty response with status code 204 if successful.
    """

    permission = 'orgs.org_api'

    def post(self, request, *args, **kwargs):
        body = request.data
        device_token = body.get('device_token', None)
        user = request.user

        if not device_token:
            return JsonResponse({'errors': [_('device_token field is required')]}, safe=False, status=status.HTTP_400_BAD_REQUEST)

        errors = []

        try:
            device_token_args = dict(device_token=device_token,
                                     user=user)
            DeviceToken.get_or_create(**device_token_args)
        except Exception as e:
            errors.append(e.args)

        if errors:
            return JsonResponse({'errors': errors}, safe=False, status=status.HTTP_400_BAD_REQUEST,
                                json_dumps_params={'indent': 2})
        else:
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    @classmethod
    def get_write_explorer(cls):
        return {
            'method': "POST",
            'title': "Action to add device token to user",
            'url': reverse('api.v3.device_token'),
            'slug': 'device-token',
            'fields': [dict(name='device_token', required=True,
                            help="The user device token")],
            'example': {'body': '{"device_token": "123456789987654321"}'},
        }


class CreateAccountView(SmartFormView):
    """
    Action to add device tokens to user
    """

    class RegisterForm(forms.Form):
        surveyor_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Surveyor Password'}))
        first_name = forms.CharField(help_text=_("Your first name"), widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
        last_name = forms.CharField(help_text=_("Your last name"), widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
        email = forms.EmailField(help_text=_("Your email address"), widget=forms.TextInput(attrs={'placeholder': 'Email'}))
        password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
                                   help_text=_("Your password, at least eight letters please"))

        def __init__(self, *args, **kwargs):
            super(CreateAccountView.RegisterForm, self).__init__(*args, **kwargs)

        def clean_surveyor_password(self):
            password = self.cleaned_data['surveyor_password']
            org = Org.objects.filter(surveyor_password=password).first()
            if not org:
                password_error = _("Invalid surveyor password, please check with your project leader and try again.")
                self.cleaned_data['password_error'] = dict(field='surveyor_password', message=password_error)
                raise forms.ValidationError(password_error)
            self.cleaned_data['org'] = org
            return password

        def clean_email(self):
            email = self.cleaned_data.get('email')
            if email:
                if User.objects.filter(username__iexact=email):
                    email_error = _("That email address is already used")
                    self.cleaned_data['register_email_error'] = dict(field='email', message=email_error)
                    raise forms.ValidationError(email_error)

            return email.lower()

        def clean_password(self):
            password = self.cleaned_data.get('password')
            if password:
                if not len(password) >= 8:
                    password_error = _("Passwords must contain at least 8 letters.")
                    self.cleaned_data['register_password_error'] = dict(field='password', message=password_error)
                    raise forms.ValidationError(password_error)
            return password

    permission = None
    form_class = RegisterForm

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(CreateAccountView, self).dispatch(*args, **kwargs)

    def form_invalid(self, form):
        errors = []
        register_email_error = form.cleaned_data.get('register_email_error', None)
        register_password_error = form.cleaned_data.get('register_password_error', None)
        password_error = form.cleaned_data.get('password_error', None)

        if password_error:
            errors.append(password_error)
        if register_email_error:
            errors.append(register_email_error)
        if register_password_error:
            errors.append(register_password_error)

        return JsonResponse(dict(errors=errors), safe=False, status=status.HTTP_400_BAD_REQUEST,
                            json_dumps_params={'indent': 2})

    def form_valid(self, form):
        # create our user
        username = self.form.cleaned_data['email']
        user = Org.create_user(username, self.form.cleaned_data['password'])

        user.first_name = self.form.cleaned_data['first_name']
        user.last_name = self.form.cleaned_data['last_name']
        user.is_active = False
        user.save()

        # log the user in
        user = authenticate(username=user.username, password=self.form.cleaned_data['password'])

        org = self.form.cleaned_data['org']
        org.surveyors.add(user)

        # Creating a API token to the user
        role = APIToken.get_role_from_code('S')
        APIToken.get_or_create(org, user, role=role)

        # Sending push notifications via FCM to surveyor admin users
        tokens = []
        for admin in org.administrators.all():
            for token in admin.device_tokens.filter(is_active=True):
                tokens.append(token.device_token)

        push_notification_to_fcm.delay(tokens)

        return JsonResponse(dict(), safe=False, status=status.HTTP_204_NO_CONTENT)


class RecoveryPasswordView(SmartFormView):
    """
    Action to request to change the user password
    """

    class UserForgetForm(forms.Form):
        email = forms.EmailField(label=_("Your Email"), )

        def clean_email(self):
            email = self.cleaned_data['email'].strip()

            user = User.objects.filter(email__iexact=email).first()
            if not user:
                email_error = _("We didn't find an user with that email. Please, try again.")
                self.cleaned_data['email_error'] = dict(field='email', message=email_error)
                raise forms.ValidationError(email_error)

            return email

    permission = None
    form_class = UserForgetForm

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(RecoveryPasswordView, self).dispatch(*args, **kwargs)

    def form_invalid(self, form):
        errors = []
        email_error = form.cleaned_data.get('email_error', None)

        if email_error:
            errors.append(email_error)

        return JsonResponse(dict(errors=errors), safe=False, status=status.HTTP_400_BAD_REQUEST)

    def form_valid(self, form):
        email = form.cleaned_data['email']

        user = User.objects.filter(email__iexact=email).first()

        context = build_email_context(self.request, user)

        if user:
            token = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
            RecoveryToken.objects.create(token=token, user=user)
            FailedLogin.objects.filter(user=user).delete()
            context['user'] = dict(username=user.username)
            context['path'] = "%s" % reverse('users.user_recover', args=[token])

            send_recovery_mail.delay(context, [email])

            return JsonResponse(dict(), safe=False, status=status.HTTP_204_NO_CONTENT)

        else:
            return JsonResponse(dict(
                errors={'email': _('User not found')}),
                safe=False,
                status=status.HTTP_400_BAD_REQUEST
            )


class CustomEndpoints(ListAPIMixin, BaseAPIView):
    """
    ## Create Account
    /api/v3/create_account - to create account through multipart form request

    A **POST** can be used to perform an action to create accounts

    * **surveyor_password** - the org surveyor password
    * **first_name** - the first name of the user
    * **last_name** - the last name of the user
    * **email** - the email of the user
    * **password** - the user password

    Example:

        curl --request POST \\
             --url http://example.com/api/v3/create_account.json \\
             --form surveyor_password=12345 \\
             --form first_name=John \\
             --form 'last_name=Bolton' \\
             --form email=johnbolton@example.com \\
             --form password=12345

    ## Manage Accounts
    /api/v3/manage_accounts/list - to list accounts pending of approbation

    A **GET** can be used to list the accounts pending of approbation

    * **id** - the ID of the user
    * **username** - the username of the account

    Example:

        curl --request GET \\
             --url http://example.com/api/v3/manage_accounts/list.json \\
             --header 'authorization: Token your-token-here'

    ## User Orgs
    /api/v3/user/orgs - to list orgs of the user

    A **GET** can be used to list the orgs of the user

    * **id** - the org object
    * **token** - the token that this user could access that org's APIs

    Example:

        curl --request GET \\
             --url http://example.com/api/v3/user/orgs.json \\
             --header 'authorization: Token your-token-here'

    ## Recovery Password
    /api/v3/recovery_password - to recovery the password through multipart form request

    A **POST** can be used to perform an action to recovery or change the password

    * **email** - the email of the user

    Example:

        curl --request POST \\
             --url http://example.com/api/v3/recovery_password.json \\
             --form email=example@example.com
    """
