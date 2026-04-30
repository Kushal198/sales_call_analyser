from rest_framework import serializers
from .models import Call, AnalysisJob, CallAnalysis

class CallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Call
        fields = ['id', 'title', 'transcript', 'created_at']
        read_only_fields = ['id', 'created_at']

class CallAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallAnalysis
        fields = [
            'summary',
            'sentiment',
            'key_topics',
            'action_items',
            'objections_raised',
            'next_steps',
            'talk_ratio',
            'score',
            'score_rationale',
            'created_at',
        ]

class AnalysisJobSerializer(serializers.ModelSerializer):
    analysis = CallAnalysisSerializer(read_only=True)

    class Meta:
        model = AnalysisJob
        fields = ['id', 'call', 'status', 'error_message', 'created_at', 'analysis']
        read_only_fields = ['id', 'status', 'error_message', 'created_at']