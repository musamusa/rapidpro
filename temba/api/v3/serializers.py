from temba.flows.models import FlowRun
from ..v2.serializers import FlowRunReadSerializer as FlowRunReadSerializerV2

from rest_framework import serializers


class FlowRunReadSerializer(FlowRunReadSerializerV2):
    submitted_by = serializers.SerializerMethodField()

    def get_submitted_by(self, obj):
        return {'first_name': str(obj.submitted_by.first_name), 'last_name': str(obj.submitted_by.last_name)} if obj.submitted_by else None

    class Meta:
        model = FlowRun
        fields = ('id', 'flow', 'contact', 'start', 'responded', 'path', 'values',
                  'created_on', 'modified_on', 'exited_on', 'exit_type', 'submitted_by')
