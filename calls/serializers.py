from rest_framework import serializers
from .models import Call, AnalysisJob, CallAnalysis

class CallSerializer(serializers.ModelSerializer):
    transcript = serializers.JSONField()
    class Meta:
        model = Call
        fields = ['id', 'title', 'transcript', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_transcript(self, value):
        if not isinstance(value, list) or len(value) == 0:
            raise serializers.ValidationError("Transcript must be a non-empty list")
        for turn in value:
            if not isinstance(turn, dict):
                raise serializers.ValidationError("Each transcript turn must be an object")
            if 'speaker' not in turn or 'text' not in turn:
                raise serializers.ValidationError(
                    "Each transcript turn must have 'speaker' and 'text' fields"
                )
        return value

class CallAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallAnalysis
        fields = [
            # shared
            'summary',
            'sentiment',
            'key_topics',
            'score',
            'score_rationale',
            'skill_gaps',
            # rep-facing
            'action_items',
            'objections_raised',
            'missed_opportunities',
            'coaching_tips',
            # manager-facing
            'deal_stage_assessment',
            'recommended_manager_action',
            'created_at',
        ]

class AnalysisJobSerializer(serializers.ModelSerializer):
    analysis = CallAnalysisSerializer(read_only=True)

    class Meta:
        model = AnalysisJob
        fields = ['id', 'call', 'status', 'error_message', 'created_at', 'analysis']
        read_only_fields = ['id', 'status', 'error_message', 'created_at']