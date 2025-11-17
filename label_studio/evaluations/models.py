"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import logging
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from projects.models import Project

logger = logging.getLogger(__name__)


class Evaluation(models.Model):
    """Model to store LLM evaluation configurations and results"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
    
    class ModelProvider(models.TextChoices):
        OPENAI = 'openai', 'OpenAI'
        ANTHROPIC = 'anthropic', 'Anthropic'
        GOOGLE = 'google', 'Google'
        META = 'meta', 'Meta'
    
    # Core fields
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='evaluations',
        help_text='Project to evaluate'
    )
    
    llm_model = models.CharField(
        max_length=128,
        help_text='LLM model identifier (e.g., gpt-4, gpt-4o, gpt-4o-mini)'
    )
    
    model_provider = models.CharField(
        max_length=32,
        choices=ModelProvider.choices,
        help_text='LLM provider'
    )
    
    system_prompt = models.TextField(
        help_text='System prompt for the LLM evaluation'
    )
    
    api_key_encrypted = models.TextField(
        help_text='Encrypted API key for the LLM provider'
    )
    
    only_labeled_tasks = models.BooleanField(
        default=True,
        help_text='If True, only evaluate tasks with human labels. If False, evaluate all tasks.'
    )
    
    # Status and tracking
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    
    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    # Results
    total_tasks = models.IntegerField(
        default=0,
        help_text='Total number of tasks evaluated'
    )
    
    labeled_tasks = models.IntegerField(
        default=0,
        help_text='Number of labeled tasks in the project'
    )
    
    correct_labels = models.IntegerField(
        default=0,
        help_text='Number of labels that match LLM evaluation'
    )
    
    incorrect_labels = models.IntegerField(
        default=0,
        help_text='Number of labels that don\'t match LLM evaluation'
    )
    
    accuracy_percentage = models.FloatField(
        null=True,
        blank=True,
        help_text='Accuracy percentage of labels'
    )
    
    results = models.JSONField(
        default=dict,
        blank=True,
        help_text='Detailed evaluation results for each task'
    )
    
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error message if evaluation failed'
    )
    
    # Created by user
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='evaluations_created',
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'status']),
            models.Index(fields=['project', 'status']),
        ]
    
    def __str__(self):
        return f"Evaluation {self.id} - {self.project.title} - {self.status}"
    
    def mark_as_running(self):
        """Mark evaluation as running"""
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def mark_as_completed(self, results_data):
        """Mark evaluation as completed with results"""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.results = results_data
        
        # Calculate accuracy if we have labeled tasks
        if self.labeled_tasks > 0:
            self.accuracy_percentage = (self.correct_labels / self.labeled_tasks) * 100
        
        self.save(update_fields=[
            'status', 'completed_at', 'results', 
            'total_tasks', 'labeled_tasks', 
            'correct_labels', 'incorrect_labels', 
            'accuracy_percentage', 'updated_at'
        ])
    
    def mark_as_failed(self, error_message):
        """Mark evaluation as failed with error message"""
        self.status = self.Status.FAILED
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])
    
    def get_duration(self):
        """Get evaluation duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
