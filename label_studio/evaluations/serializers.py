"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
from rest_framework import serializers
from evaluations.models import Evaluation
from projects.models import Project
from django.conf import settings


class EvaluationCreateSerializer(serializers.Serializer):
    """Serializer for creating a new evaluation"""
    
    project_id = serializers.IntegerField(required=True)
    llm_model = serializers.CharField(required=True, max_length=128)
    system_prompt = serializers.CharField(required=True)
    api_key = serializers.CharField(required=False, write_only=True, allow_blank=True)
    use_default_api_key = serializers.BooleanField(required=False, default=False)
    
    def validate_project_id(self, value):
        """Validate project exists and user has access"""
        try:
            project = Project.objects.get(id=value)
            # Add permission check here if needed
            return value
        except Project.DoesNotExist:
            raise serializers.ValidationError("Project not found")
    
    def validate_llm_model(self, value):
        """Validate model format"""
        valid_models = [
            'gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'
        ]
        
        if value not in valid_models:
            raise serializers.ValidationError(f"Invalid model. Must be one of: {', '.join(valid_models)}")
        
        return value
    
    def validate(self, data):
        """Validate that either api_key is provided or use_default_api_key is True"""
        use_default = data.get('use_default_api_key', False)
        api_key = data.get('api_key', '')
        
        if use_default:
            # Use the default API key from settings
            if not settings.OPENAI_API_KEY:
                raise serializers.ValidationError({
                    "api_key": "Default API key is not configured in server settings"
                })
            data['api_key'] = settings.OPENAI_API_KEY
        elif not api_key or len(api_key) < 10:
            raise serializers.ValidationError({
                "api_key": "API key is required when not using default"
            })
        
        return data


class EvaluationSerializer(serializers.ModelSerializer):
    """Serializer for evaluation model"""
    
    project_title = serializers.CharField(source='project.title', read_only=True)
    project_id = serializers.IntegerField(source='project.id', read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Evaluation
        fields = [
            'id',
            'project_id',
            'project_title',
            'llm_model',
            'model_provider',
            'system_prompt',
            'status',
            'created_at',
            'updated_at',
            'started_at',
            'completed_at',
            'total_tasks',
            'labeled_tasks',
            'correct_labels',
            'incorrect_labels',
            'accuracy_percentage',
            'results',
            'error_message',
            'duration_seconds',
            'created_by_name'
        ]
        read_only_fields = [
            'id',
            'status',
            'created_at',
            'updated_at',
            'started_at',
            'completed_at',
            'total_tasks',
            'labeled_tasks',
            'correct_labels',
            'incorrect_labels',
            'accuracy_percentage',
            'results',
            'error_message'
        ]
    
    def get_duration_seconds(self, obj):
        """Get evaluation duration"""
        return obj.get_duration()


class EvaluationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing evaluations"""
    
    project_title = serializers.CharField(source='project.title', read_only=True)
    
    class Meta:
        model = Evaluation
        fields = [
            'id',
            'project_title',
            'llm_model',
            'status',
            'created_at',
            'completed_at',
            'accuracy_percentage',
            'labeled_tasks',
            'total_tasks'
        ]
