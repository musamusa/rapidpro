from temba.flows.models import FlowRun, Flow
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


class FlowReadSerializer(FlowReadSerializerV2):
    revision = serializers.ReadOnlyField(source='get_last_flow_revision')

    class Meta:
        model = Flow
        fields = FlowReadSerializerV2.Meta.fields + ('revision', 'launch_status')
