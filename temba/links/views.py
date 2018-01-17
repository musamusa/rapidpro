from __future__ import print_function, unicode_literals

import logging
import requests
import json

from django.core.urlresolvers import reverse
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from smartmin.views import SmartCRUDL, SmartCreateView, SmartListView, SmartUpdateView, SmartReadView
from temba.orgs.views import OrgPermsMixin, OrgObjPermsMixin, ModalMixin
from temba.utils import analytics
from temba.utils.views import BaseActionForm
from .models import Link

logger = logging.getLogger(__name__)


class LinkActionForm(BaseActionForm):
    allowed_actions = (('archive', _("Archive Links")),
                       ('restore', _("Restore Links")))

    model = Link
    has_is_active = True

    class Meta:
        fields = ('action', 'objects', 'add')


class LinkActionMixin(SmartListView):

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(LinkActionMixin, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        user = self.request.user
        org = user.get_org()

        form = LinkActionForm(self.request.POST, org=org, user=user)
        if form.is_valid():
            form.execute().get('changed')

        response = self.get(request, *args, **kwargs)

        return response


class BaseFlowForm(forms.ModelForm):

    class Meta:
        model = Link
        fields = '__all__'


class LinkCRUDL(SmartCRUDL):
    actions = ('list', 'read', 'archived', 'create', 'update')

    model = Link

    class OrgQuerysetMixin(object):
        def derive_queryset(self, *args, **kwargs):
            queryset = super(LinkCRUDL.OrgQuerysetMixin, self).derive_queryset(*args, **kwargs)
            if not self.request.user.is_authenticated():  # pragma: needs cover
                return queryset.exclude(pk__gt=0)
            else:
                return queryset.filter(org=self.request.user.get_org())

    class Create(ModalMixin, OrgPermsMixin, SmartCreateView):
        class LinkCreateForm(BaseFlowForm):

            def __init__(self, user, *args, **kwargs):
                super(LinkCRUDL.Create.LinkCreateForm, self).__init__(*args, **kwargs)
                self.user = user

            class Meta:
                model = Link
                fields = ('name', 'destination')

        form_class = LinkCreateForm
        success_message = ''
        field_config = dict(name=dict(help=_("Choose a name to describe this link, e.g. Luca Survey Webflow")))
        submit_button_name = _("Create")

        def get_form_kwargs(self):
            kwargs = super(LinkCRUDL.Create, self).get_form_kwargs()
            kwargs['user'] = self.request.user
            return kwargs

        def get_context_data(self, **kwargs):
            context = super(LinkCRUDL.Create, self).get_context_data(**kwargs)
            context['has_links'] = Link.objects.filter(org=self.request.user.get_org(), is_active=True).count() > 0
            return context

        def save(self, obj):
            analytics.track(self.request.user.username, 'temba.link_created', dict(name=obj.name))
            org = self.request.user.get_org()

            headers = {'Content-Type': 'application/json'}

            request_url = 'https://www.googleapis.com/urlshortener/v1/url?key=%s' % settings.GOOGLE_SHORTEN_URL_API_KEY
            response = requests.post(url=request_url,
                                     data=json.dumps(dict(longUrl='https://demo.communityconnectlabs.com')),
                                     headers=headers)
            response_json = response.json()

            self.object = Link.create(org=org, user=self.request.user, name=obj.name, destination=obj.destination,
                                      shorten_url=response_json.get('id'))

        def post_save(self, obj):
            return obj

    class Read(OrgObjPermsMixin, SmartReadView):
        slug_url_kwarg = 'uuid'
        fields = ('name',)

        def derive_title(self):
            return self.object.name

        def get_queryset(self):
            return Link.objects.filter(is_active=True)

        def get_context_data(self, **kwargs):
            context = super(LinkCRUDL.Read, self).get_context_data(**kwargs)
            return context

        def get_gear_links(self):
            links = []

            if self.has_org_perm("links.link_update"):
                links.append(dict(title=_('Edit'), style='btn-primary', js_class='update-link', href="#"))

            return links

    class Update(ModalMixin, OrgObjPermsMixin, SmartUpdateView):
        class LinkUpdateForm(BaseFlowForm):

            def __init__(self, user, *args, **kwargs):
                super(LinkCRUDL.Update.LinkUpdateForm, self).__init__(*args, **kwargs)
                self.user = user

            class Meta:
                model = Link
                fields = ('name', 'destination')

        success_message = ''
        success_url = 'uuid@links.link_read'
        fields = ('name', 'destination')
        form_class = LinkUpdateForm

        def derive_fields(self):
            fields = [field for field in self.fields]
            return fields

        def get_form_kwargs(self):
            kwargs = super(LinkCRUDL.Update, self).get_form_kwargs()
            kwargs['user'] = self.request.user
            return kwargs

        def pre_save(self, obj):
            obj = super(LinkCRUDL.Update, self).pre_save(obj)
            return obj

        def post_save(self, obj):
            return obj

    class BaseList(LinkActionMixin, OrgQuerysetMixin, OrgPermsMixin, SmartListView):
        title = _("Trackable Links")
        refresh = 10000
        fields = ('name', 'modified_on')
        default_template = 'links/link_list.html'
        default_order = ('-created_on')
        search_fields = ('name__icontains',)

        def get_context_data(self, **kwargs):
            context = super(LinkCRUDL.BaseList, self).get_context_data(**kwargs)
            context['org_has_links'] = Link.objects.filter(org=self.request.user.get_org(), is_active=True).count()
            context['folders'] = self.get_folders()
            context['request_url'] = self.request.path
            context['actions'] = self.actions

            return context

        def derive_queryset(self, *args, **kwargs):
            qs = super(LinkCRUDL.BaseList, self).derive_queryset(*args, **kwargs)
            return qs.exclude(is_active=False)

        def get_folders(self):
            org = self.request.user.get_org()

            return [
                dict(label="Active", url=reverse('links.link_list'),
                     count=Link.objects.filter(is_active=True, is_archived=False, org=org).count()),

                dict(label="Archived", url=reverse('links.link_archived'),
                     count=Link.objects.filter(is_active=True, is_archived=True, org=org).count())
            ]

    class Archived(BaseList):
        actions = ('restore',)
        default_order = ('-created_on',)

        def derive_queryset(self, *args, **kwargs):
            return super(LinkCRUDL.Archived, self).derive_queryset(*args, **kwargs).filter(is_active=True, is_archived=True)

    class List(BaseList):
        title = _("Trackable Links")
        actions = ('archive',)

        def derive_queryset(self, *args, **kwargs):
            queryset = super(LinkCRUDL.List, self).derive_queryset(*args, **kwargs)
            queryset = queryset.filter(is_active=True, is_archived=False)
            return queryset
