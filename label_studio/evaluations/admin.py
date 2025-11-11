"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
from django.contrib import admin
from evaluations.models import Evaluation


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'project',
        'llm_model',
        'status',
        'accuracy_percentage',
        'labeled_tasks',
        'created_at',
        'created_by'
    ]
    list_filter = ['status', 'model_provider', 'created_at']
    search_fields = ['project__title', 'llm_model']
    readonly_fields = [
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
    fieldsets = (
        ('Basic Information', {
            'fields': ('project', 'llm_model', 'model_provider', 'system_prompt', 'created_by')
        }),
        ('Status', {
            'fields': ('status', 'created_at', 'updated_at', 'started_at', 'completed_at')
        }),
        ('Results', {
            'fields': (
                'total_tasks', 
                'labeled_tasks', 
                'correct_labels', 
                'incorrect_labels', 
                'accuracy_percentage'
            )
        }),
        ('Details', {
            'fields': ('results', 'error_message'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Disable adding through admin - use API instead
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion of old evaluations
        return True
