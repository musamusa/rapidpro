from __future__ import print_function, unicode_literals

import logging
import regex

from django.core.urlresolvers import reverse
from django.db.models import Count
from django import forms
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _

from smartmin.views import SmartCRUDL, SmartCreateView, SmartListView, SmartUpdateView, smart_url
from smartmin.views import SmartDeleteView
from temba.orgs.views import OrgPermsMixin, OrgObjPermsMixin, ModalMixin
from temba.triggers.models import Trigger
from temba.utils import analytics, on_transaction_commit
from .models import TrackableLink

logger = logging.getLogger(__name__)


class BaseFlowForm(forms.ModelForm):
    def clean_keyword_triggers(self):
        org = self.user.get_org()
        value = self.cleaned_data.get('keyword_triggers', '')

        duplicates = []
        wrong_format = []
        cleaned_keywords = []

        for keyword in value.split(','):
            keyword = keyword.lower().strip()
            if not keyword:
                continue

            if not regex.match('^\w+$', keyword, flags=regex.UNICODE | regex.V0) or len(keyword) > Trigger.KEYWORD_MAX_LEN:
                wrong_format.append(keyword)

            # make sure it is unique on this org
            existing = Trigger.objects.filter(org=org, keyword__iexact=keyword, is_archived=False, is_active=True)
            if self.instance:
                existing = existing.exclude(flow=self.instance.pk)

            if existing:
                duplicates.append(keyword)
            else:
                cleaned_keywords.append(keyword)

        if wrong_format:
            raise forms.ValidationError(_('"%s" must be a single word, less than %d characters, containing only letter '
                                          'and numbers') % (', '.join(wrong_format), Trigger.KEYWORD_MAX_LEN))

        if duplicates:
            if len(duplicates) > 1:
                error_message = _('The keywords "%s" are already used for another flow') % ', '.join(duplicates)
            else:
                error_message = _('The keyword "%s" is already used for another flow') % ', '.join(duplicates)
            raise forms.ValidationError(error_message)

        return ','.join(cleaned_keywords)

    class Meta:
        model = Flow
        fields = '__all__'


class LinkCRUDL(SmartCRUDL):
    actions = ('list', 'archived', 'create', 'delete', 'update')

    model = TrackableLink

    class Create(ModalMixin, OrgPermsMixin, SmartCreateView):
        class FlowCreateForm(BaseFlowForm):
            keyword_triggers = forms.CharField(required=False, label=_("Global keyword triggers"),
                                               help_text=_("When a user sends any of these keywords they will begin this flow"))

            flow_type = forms.ChoiceField(label=_('Run flow over'),
                                          help_text=_('Send messages, place phone calls, or submit Surveyor runs'),
                                          choices=((Flow.FLOW, 'Messaging'),
                                                   (Flow.USSD, 'USSD Messaging'),
                                                   (Flow.VOICE, 'Phone Call'),
                                                   (Flow.SURVEY, 'Surveyor')))

            def __init__(self, user, *args, **kwargs):
                super(FlowCRUDL.Create.FlowCreateForm, self).__init__(*args, **kwargs)
                self.user = user

                org_languages = self.user.get_org().languages.all().order_by('orgs', 'name')
                language_choices = ((lang.iso_code, lang.name) for lang in org_languages)
                self.fields['base_language'] = forms.ChoiceField(label=_('Language'),
                                                                 initial=self.user.get_org().primary_language,
                                                                 choices=language_choices)

            class Meta:
                model = Flow
                fields = ('name', 'keyword_triggers', 'flow_type', 'base_language')

        form_class = FlowCreateForm
        success_url = 'uuid@flows.flow_editor'
        success_message = ''
        field_config = dict(name=dict(help=_("Choose a name to describe this flow, e.g. Demographic Survey")))

        def derive_exclude(self):
            org = self.request.user.get_org()
            exclude = []

            if not org.primary_language:
                exclude.append('base_language')

            return exclude

        def get_form_kwargs(self):
            kwargs = super(FlowCRUDL.Create, self).get_form_kwargs()
            kwargs['user'] = self.request.user
            return kwargs

        def get_context_data(self, **kwargs):
            context = super(FlowCRUDL.Create, self).get_context_data(**kwargs)
            context['has_flows'] = Flow.objects.filter(org=self.request.user.get_org(), is_active=True).count() > 0
            return context

        def save(self, obj):
            analytics.track(self.request.user.username, 'temba.flow_created', dict(name=obj.name))
            org = self.request.user.get_org()

            if not obj.flow_type:  # pragma: needs cover
                obj.flow_type = Flow.FLOW

            # if we don't have a language, use base
            if not obj.base_language:  # pragma: needs cover
                obj.base_language = 'base'

            # default expiration is a week
            expires_after_minutes = 60 * 24 * 7
            if obj.flow_type == Flow.VOICE:
                # ivr expires after 5 minutes of inactivity
                expires_after_minutes = 5

            self.object = Flow.create(org, self.request.user, obj.name,
                                      flow_type=obj.flow_type, expires_after_minutes=expires_after_minutes,
                                      base_language=obj.base_language)

        def post_save(self, obj):
            user = self.request.user
            org = user.get_org()

            # create triggers for this flow only if there are keywords and we aren't a survey
            if self.form.cleaned_data.get('flow_type') != Flow.SURVEY:
                if len(self.form.cleaned_data['keyword_triggers']) > 0:
                    for keyword in self.form.cleaned_data['keyword_triggers'].split(','):
                        Trigger.objects.create(org=org, keyword=keyword, flow=obj, created_by=user, modified_by=user)

            return obj

    class Delete(ModalMixin, OrgObjPermsMixin, SmartDeleteView):
        fields = ('id',)
        cancel_url = 'uuid@flows.flow_editor'
        success_message = ''

        def get_success_url(self):
            return reverse("flows.flow_list")

        def post(self, request, *args, **kwargs):
            flow = self.get_object()
            self.object = flow

            flows = Flow.objects.filter(org=flow.org, flow_dependencies__in=[flow])
            if flows.count():
                return HttpResponseRedirect(smart_url(self.cancel_url, flow))

            # do the actual deletion
            flow.release()

            # we can't just redirect so as to make our modal do the right thing
            response = self.render_to_response(self.get_context_data(success_url=self.get_success_url(),
                                                                     success_script=getattr(self, 'success_script', None)))
            response['Temba-Success'] = self.get_success_url()

            return response

    class Update(ModalMixin, OrgObjPermsMixin, SmartUpdateView):
        class FlowUpdateForm(BaseFlowForm):

            expires_after_minutes = forms.ChoiceField(label=_('Expire inactive contacts'),
                                                      help_text=_(
                                                          "When inactive contacts should be removed from the flow"),
                                                      initial=str(60 * 24 * 7),
                                                      choices=EXPIRES_CHOICES)

            def __init__(self, user, *args, **kwargs):
                super(FlowCRUDL.Update.FlowUpdateForm, self).__init__(*args, **kwargs)
                self.user = user

                metadata = self.instance.get_metadata_json()
                flow_triggers = Trigger.objects.filter(
                    org=self.instance.org, flow=self.instance, is_archived=False, groups=None,
                    trigger_type=Trigger.TYPE_KEYWORD
                ).order_by('created_on')

                if self.instance.flow_type == Flow.VOICE:
                    expiration = self.fields['expires_after_minutes']
                    expiration.choices = IVR_EXPIRES_CHOICES
                    expiration.initial = 5

                # if we don't have a base language let them pick one (this is immutable)
                if not self.instance.base_language:
                    choices = [('', 'No Preference')]
                    choices += [(lang.iso_code, lang.name) for lang in self.instance.org.languages.all().order_by('orgs', 'name')]
                    self.fields['base_language'] = forms.ChoiceField(label=_('Language'), choices=choices)

                if self.instance.flow_type == Flow.SURVEY:
                    contact_creation = forms.ChoiceField(
                        label=_('Create a contact '),
                        initial=metadata.get(Flow.CONTACT_CREATION, Flow.CONTACT_PER_RUN),
                        help_text=_("Whether surveyor logins should be used as the contact for each run"),
                        choices=(
                            (Flow.CONTACT_PER_RUN, _('For each run')),
                            (Flow.CONTACT_PER_LOGIN, _('For each login'))
                        )
                    )

                    self.fields[Flow.CONTACT_CREATION] = contact_creation
                else:
                    self.fields['keyword_triggers'] = forms.CharField(required=False,
                                                                      label=_("Global keyword triggers"),
                                                                      help_text=_("When a user sends any of these keywords they will begin this flow"),
                                                                      initial=','.join([t.keyword for t in flow_triggers]))

            class Meta:
                model = Flow
                fields = ('name', 'labels', 'base_language', 'expires_after_minutes', 'ignore_triggers')

        success_message = ''
        fields = ('name', 'expires_after_minutes')
        form_class = FlowUpdateForm

        def derive_fields(self):
            fields = [field for field in self.fields]

            obj = self.get_object()
            if not obj.base_language and self.org.primary_language:  # pragma: needs cover
                fields += ['base_language']

            if obj.flow_type == Flow.SURVEY:
                fields.insert(len(fields) - 1, Flow.CONTACT_CREATION)
            else:
                fields.insert(1, 'keyword_triggers')
                fields.append('ignore_triggers')

            return fields

        def get_form_kwargs(self):
            kwargs = super(FlowCRUDL.Update, self).get_form_kwargs()
            kwargs['user'] = self.request.user
            return kwargs

        def pre_save(self, obj):
            obj = super(FlowCRUDL.Update, self).pre_save(obj)
            metadata = obj.get_metadata_json()

            if Flow.CONTACT_CREATION in self.form.cleaned_data:
                metadata[Flow.CONTACT_CREATION] = self.form.cleaned_data[Flow.CONTACT_CREATION]
            obj.set_metadata_json(metadata)
            return obj

        def post_save(self, obj):
            keywords = set()
            user = self.request.user
            org = user.get_org()

            if 'keyword_triggers' in self.form.cleaned_data:

                existing_keywords = set(t.keyword for t in obj.triggers.filter(org=org, flow=obj,
                                                                               trigger_type=Trigger.TYPE_KEYWORD,
                                                                               is_archived=False, groups=None))

                if len(self.form.cleaned_data['keyword_triggers']) > 0:
                    keywords = set(self.form.cleaned_data['keyword_triggers'].split(','))

                removed_keywords = existing_keywords.difference(keywords)
                for keyword in removed_keywords:
                    obj.triggers.filter(org=org, flow=obj, keyword=keyword,
                                        groups=None, is_archived=False).update(is_archived=True)

                added_keywords = keywords.difference(existing_keywords)
                archived_keywords = [t.keyword for t in obj.triggers.filter(org=org, flow=obj, trigger_type=Trigger.TYPE_KEYWORD,
                                                                            is_archived=True, groups=None)]
                for keyword in added_keywords:
                    # first check if the added keyword is not amongst archived
                    if keyword in archived_keywords:  # pragma: needs cover
                        obj.triggers.filter(org=org, flow=obj, keyword=keyword, groups=None).update(is_archived=False)
                    else:
                        Trigger.objects.create(org=org, keyword=keyword, trigger_type=Trigger.TYPE_KEYWORD,
                                               flow=obj, created_by=user, modified_by=user)

            # run async task to update all runs
            from .tasks import update_run_expirations_task
            on_transaction_commit(lambda: update_run_expirations_task.delay(obj.pk))

            return obj

    class BaseList(FlowActionMixin, OrgQuerysetMixin, OrgPermsMixin, SmartListView):
        title = _("Trackable Links")
        refresh = 10000
        fields = ('name', 'modified_on')
        default_template = 'flows/flow_list.html'
        default_order = ('-saved_on',)
        search_fields = ('name__icontains',)

        def get_context_data(self, **kwargs):
            context = super(FlowCRUDL.BaseList, self).get_context_data(**kwargs)
            context['org_has_flows'] = Flow.objects.filter(org=self.request.user.get_org(), is_active=True).count()
            context['folders'] = self.get_folders()
            context['labels'] = self.get_flow_labels()
            context['campaigns'] = self.get_campaigns()
            context['request_url'] = self.request.path
            context['actions'] = self.actions

            # decorate flow objects with their run activity stats
            for flow in context['object_list']:
                flow.run_stats = flow.get_run_stats()

            return context

        def derive_queryset(self, *args, **kwargs):
            qs = super(FlowCRUDL.BaseList, self).derive_queryset(*args, **kwargs)
            return qs.exclude(flow_type=Flow.MESSAGE).exclude(is_active=False)

        def get_campaigns(self):
            from temba.campaigns.models import CampaignEvent
            org = self.request.user.get_org()
            events = CampaignEvent.objects.filter(campaign__org=org, is_active=True, campaign__is_active=True,
                                                  flow__is_archived=False, flow__is_active=True, flow__flow_type=Flow.FLOW)
            return events.values('campaign__name', 'campaign__id').annotate(count=Count('id')).order_by('campaign__name')

        def get_flow_labels(self):
            labels = []
            for label in FlowLabel.objects.filter(org=self.request.user.get_org(), parent=None):
                labels.append(dict(pk=label.pk, label=label.name, count=label.get_flows_count(), children=label.children.all()))
            return labels

        def get_folders(self):
            org = self.request.user.get_org()

            return [
                dict(label="Active", url=reverse('flows.flow_list'),
                     count=Flow.objects.exclude(flow_type=Flow.MESSAGE).filter(is_active=True,
                                                                               is_archived=False,
                                                                               org=org).count()),
                dict(label="Archived", url=reverse('flows.flow_archived'),
                     count=Flow.objects.exclude(flow_type=Flow.MESSAGE).filter(is_active=True,
                                                                               is_archived=True,
                                                                               org=org).count())
            ]

    class Archived(BaseList):
        actions = ('restore',)
        default_order = ('-created_on',)

        def derive_queryset(self, *args, **kwargs):
            return super(FlowCRUDL.Archived, self).derive_queryset(*args, **kwargs).filter(is_active=True, is_archived=True)

    class List(BaseList):
        title = _("Flows")
        actions = ('archive', 'label')

        def derive_queryset(self, *args, **kwargs):
            queryset = super(FlowCRUDL.List, self).derive_queryset(*args, **kwargs)
            queryset = queryset.filter(is_active=True, is_archived=False)
            types = self.request.GET.getlist('flow_type')
            if types:
                queryset = queryset.filter(flow_type__in=types)
            return queryset
