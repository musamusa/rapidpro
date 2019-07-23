from temba.flows.models import FlowRun, Flow, FlowStep
from temba.contacts.models import Contact, URN, TEL_SCHEME
from ..v1.serializers import FlowRunWriteSerializer as FlowRunWriteSerializerV1
from ..v1.serializers import ContactWriteSerializer as ContactWriteSerializerV1
from ..v2.serializers import FlowRunReadSerializer as FlowRunReadSerializerV2
from ..v2.serializers import FlowReadSerializer as FlowReadSerializerV2

from rest_framework import serializers


class FlowRunReadSerializer(FlowRunReadSerializerV2):
    submitted_by = serializers.SerializerMethodField()

    def get_submitted_by(self, obj):
        return {'first_name': str(obj.submitted_by.first_name), 'last_name': str(obj.submitted_by.last_name)} if obj.submitted_by else None

    class Meta:
        model = FlowRun
        fields = FlowRunReadSerializerV2.Meta.fields + ('submitted_by',)


class FlowRunWriteSerializer(FlowRunWriteSerializerV1):

    def save(self):
        started = self.validated_data['started']
        steps = self.validated_data.get('steps', [])
        completed = self.validated_data.get('completed', False)

        if self.flow_obj.launch_status == Flow.STATUS_PRODUCTION:
            # look for previous run with this contact and flow
            run = FlowRun.objects.filter(org=self.org, contact=self.contact_obj, submitted_by=self.user,
                                         flow=self.flow_obj, created_on=started).order_by('-modified_on').first()

            if not run:
                run = FlowRun.create(self.flow_obj, self.contact_obj.pk, created_on=started,
                                     submitted_by=self.user)

            step_objs = []
            previous_rule = None
            for step in steps:
                step_obj = FlowStep.from_json(step, self.flow_obj, run, previous_rule)
                previous_rule = step_obj.rule_uuid
                step_objs.append(step_obj)

            if completed:
                final_step = step_objs[len(step_objs) - 1] if step_objs else None
                completed_on = steps[len(steps) - 1]['arrived_on'] if steps else None

                run.set_completed(final_step, completed_on=completed_on)
            else:
                run.save(update_fields=('modified_on',))

            return run
        else:
            return None


class FlowReadSerializer(FlowReadSerializerV2):
    revision = serializers.ReadOnlyField(source='get_last_flow_revision')

    class Meta:
        model = Flow
        fields = FlowReadSerializerV2.Meta.fields + ('revision', 'launch_status')


class ContactWriteSerializer(ContactWriteSerializerV1):

    def validate_urns(self, value):
        if value is not None:
            org = self.context['org']
            self.parsed_urns = []

            # this field isn't allowed if we are looking up by URN in the URL
            if 'urns__identity' in self.context['lookup_values']:
                raise serializers.ValidationError("Field not allowed when using URN in URL")

            # or for updates by anonymous organizations (we do allow creation of contacts with URNs)
            if org.is_anon and self.instance:
                raise serializers.ValidationError("Updating URNs not allowed for anonymous organizations")

            # if creating a contact, URNs can't belong to other contacts
            if not self.instance:
                for urn in value:
                    if Contact.from_urn(org, urn):
                        raise serializers.ValidationError("URN belongs to another contact: %s" % urn)

            for urn in value:
                try:
                    normalized = URN.normalize(urn)
                    scheme, path, display = URN.to_parts(normalized)
                    # for backwards compatibility we don't validate phone numbers here
                    if scheme != TEL_SCHEME and not URN.validate(normalized):  # pragma: needs cover
                        raise ValueError()
                except ValueError:
                    raise serializers.ValidationError("Invalid URN: '%s'" % urn)

                self.parsed_urns.append(normalized)

        return value
