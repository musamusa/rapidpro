from rest_framework.urlpatterns import format_suffix_patterns

from django.conf.urls import url

from .views import (
    ArchivesEndpoint,
    AuthenticateView,
    BoundariesEndpoint,
    BroadcastsEndpoint,
    CampaignEventsEndpoint,
    CampaignsEndpoint,
    ChannelEventsEndpoint,
    ChannelsEndpoint,
    ClassifiersEndpoint,
    ContactActionsEndpoint,
    ContactsEndpoint,
    DefinitionsEndpoint,
    ExplorerView,
    FieldsEndpoint,
    FlowsEndpoint,
    FlowStartsEndpoint,
    GlobalsEndpoint,
    GroupsEndpoint,
    LabelsEndpoint,
    MediaEndpoint,
    MessageActionsEndpoint,
    MessagesEndpoint,
    ResthookEventsEndpoint,
    ResthooksEndpoint,
    ResthookSubscribersEndpoint,
    RootView,
    RunsEndpoint,
    TemplatesEndpoint,
    ValidateUrlAttachmentEndpoint,
    TicketersEndpoint,
    WorkspaceEndpoint,
    ParseDatabaseEndpoint,
    ParseDatabaseRecordsEndpoint,
    # reporting endpoints
    ContactsReportEndpoint,
    MessagesReportEndpoint,
    FlowReportEndpoint,
    FlowVariableReportEndpoint,
    ContactVariablesReportEndpoint,
    TrackableLinkReportEndpoint,
)

urlpatterns = [
    url(r"^$", RootView.as_view(), name="api.v2"),
    url(r"^explorer/$", ExplorerView.as_view(), name="api.v2.explorer"),
    url(r"^authenticate$", AuthenticateView.as_view(), name="api.v2.authenticate"),
    # ========== endpoints A-Z ===========
    url(r"^archives$", ArchivesEndpoint.as_view(), name="api.v2.archives"),
    url(r"^boundaries$", BoundariesEndpoint.as_view(), name="api.v2.boundaries"),
    url(r"^broadcasts$", BroadcastsEndpoint.as_view(), name="api.v2.broadcasts"),
    url(r"^campaigns$", CampaignsEndpoint.as_view(), name="api.v2.campaigns"),
    url(r"^campaign_events$", CampaignEventsEndpoint.as_view(), name="api.v2.campaign_events"),
    url(r"^channels$", ChannelsEndpoint.as_view(), name="api.v2.channels"),
    url(r"^channel_events$", ChannelEventsEndpoint.as_view(), name="api.v2.channel_events"),
    url(r"^classifiers$", ClassifiersEndpoint.as_view(), name="api.v2.classifiers"),
    url(r"^contacts$", ContactsEndpoint.as_view(), name="api.v2.contacts"),
    url(r"^contact_actions$", ContactActionsEndpoint.as_view(), name="api.v2.contact_actions"),
    url(r"^database$", ParseDatabaseEndpoint.as_view(), name="api.v2.parse_database"),
    url(r"^database_records$", ParseDatabaseRecordsEndpoint.as_view(), name="api.v2.parse_database_records"),
    url(r"^definitions$", DefinitionsEndpoint.as_view(), name="api.v2.definitions"),
    url(r"^fields$", FieldsEndpoint.as_view(), name="api.v2.fields"),
    url(r"^flow_starts$", FlowStartsEndpoint.as_view(), name="api.v2.flow_starts"),
    url(r"^flows$", FlowsEndpoint.as_view(), name="api.v2.flows"),
    url(r"^globals$", GlobalsEndpoint.as_view(), name="api.v2.globals"),
    url(r"^groups$", GroupsEndpoint.as_view(), name="api.v2.groups"),
    url(r"^labels$", LabelsEndpoint.as_view(), name="api.v2.labels"),
    url(r"^media$", MediaEndpoint.as_view(), name="api.v2.media"),
    url(r"^messages$", MessagesEndpoint.as_view(), name="api.v2.messages"),
    url(r"^message_actions$", MessageActionsEndpoint.as_view(), name="api.v2.message_actions"),
    url(r"^org$", WorkspaceEndpoint.as_view(), name="api.v2.org"),  # deprecated
    url(r"^resthooks$", ResthooksEndpoint.as_view(), name="api.v2.resthooks"),
    url(r"^resthook_events$", ResthookEventsEndpoint.as_view(), name="api.v2.resthook_events"),
    url(r"^resthook_subscribers$", ResthookSubscribersEndpoint.as_view(), name="api.v2.resthook_subscribers"),
    url(r"^runs$", RunsEndpoint.as_view(), name="api.v2.runs"),
    url(r"^templates$", TemplatesEndpoint.as_view(), name="api.v2.templates"),
    url(r"^ticketers$", TicketersEndpoint.as_view(), name="api.v2.ticketers"),
    url(r"^workspace$", WorkspaceEndpoint.as_view(), name="api.v2.workspace"),
    url(r"^validate_attachment_url$", ValidateUrlAttachmentEndpoint.as_view(), name="api.v2.attachments_validation"),
    url(r"^contacts_report$", ContactsReportEndpoint.as_view(), name="api.v2.contacts_report"),
    url(r"^messages_report$", MessagesReportEndpoint.as_view(), name="api.v2.messages_report"),
    url(r"^flow_report$", FlowReportEndpoint.as_view(), name="api.v2.flow_report"),
    url(r"^flow_variable_report$", FlowVariableReportEndpoint.as_view(), name="api.v2.flow_variable_report"),
    url(r"^contact_variable_report$", ContactVariablesReportEndpoint.as_view(), name="api.v2.contact_variable_report"),
    url(r"^trackable_link_report$", TrackableLinkReportEndpoint.as_view(), name="api.v2.trackable_link_report"),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=["json", "api"])
