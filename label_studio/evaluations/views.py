"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import logging
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import HttpResponse

from evaluations.models import Evaluation
from evaluations.serializers import (
    EvaluationSerializer,
    EvaluationListSerializer,
    EvaluationCreateSerializer
)
from evaluations.tasks import run_evaluation_async
from evaluations.services import EvaluationService
from projects.models import Project

logger = logging.getLogger(__name__)


class EvaluationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing LLM evaluations"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = EvaluationSerializer
    
    def get_queryset(self):
        """Get evaluations for current user's organization"""
        user = self.request.user
        # Filter by user's accessible projects
        return Evaluation.objects.filter(
            project__organization=user.active_organization
        ).select_related('project', 'created_by')
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return EvaluationListSerializer
        elif self.action == 'create':
            return EvaluationCreateSerializer
        return EvaluationSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create and start a new evaluation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        project_id = data['project_id']
        llm_model = data['llm_model']
        system_prompt = data['system_prompt']
        api_key = data['api_key']
        only_labeled_tasks = data.get('only_labeled_tasks', True)
        
        # Get project
        project = get_object_or_404(
            Project.objects.filter(organization=request.user.active_organization),
            id=project_id
        )
        
        # Determine provider from model
        provider = self._get_provider_from_model(llm_model)
        
        # Validate API key
        eval_service = EvaluationService()
        
        is_valid, error_msg = eval_service.validate_api_key(provider, api_key, llm_model)
        if not is_valid:
            return Response(
                {'error': f'Invalid API key: {error_msg}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Encrypt API key
        encrypted_key = eval_service.encrypt_api_key(api_key)
        
        # Create evaluation record
        evaluation = Evaluation.objects.create(
            project=project,
            llm_model=llm_model,
            model_provider=provider,
            system_prompt=system_prompt,
            api_key_encrypted=encrypted_key,
            only_labeled_tasks=only_labeled_tasks,
            status=Evaluation.Status.PENDING,
            created_by=request.user
        )
        
        # Start async evaluation task
        try:
            run_evaluation_async(evaluation.id)
            logger.info(f"Started evaluation {evaluation.id} for project {project.id}")
        except Exception as e:
            logger.error(f"Failed to start evaluation: {str(e)}")
            evaluation.mark_as_failed(f"Failed to start evaluation: {str(e)}")
        
        # Return created evaluation
        output_serializer = EvaluationSerializer(evaluation)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get detailed results for an evaluation"""
        evaluation = self.get_object()
        
        if evaluation.status != Evaluation.Status.COMPLETED:
            return Response(
                {'error': 'Evaluation not completed yet'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(evaluation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running evaluation"""
        evaluation = self.get_object()
        
        if evaluation.status not in [Evaluation.Status.PENDING, Evaluation.Status.RUNNING]:
            return Response(
                {'error': 'Cannot cancel evaluation in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        evaluation.mark_as_failed("Cancelled by user")
        return Response({'status': 'cancelled'})
    
    @action(detail=False, methods=['get'])
    def by_project(self, request):
        """Get evaluations for a specific project"""
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response(
                {'error': 'project_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        evaluations = self.get_queryset().filter(project_id=project_id)
        serializer = EvaluationListSerializer(evaluations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download_report(self, request, pk=None):
        """Download PDF report for completed evaluation"""
        evaluation = self.get_object()
        
        if evaluation.status != Evaluation.Status.COMPLETED:
            return Response(
                {'error': 'Evaluation not completed yet. Cannot generate report.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not evaluation.results:
            return Response(
                {'error': 'No results available for this evaluation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Prepare evaluation data for PDF
            evaluation_data = {
                'project_title': evaluation.project.title,
                'llm_model': evaluation.llm_model,
                'status': evaluation.get_status_display(),
                'total_tasks': evaluation.total_tasks or 0,
                'labeled_tasks': evaluation.labeled_tasks or 0,
                'accuracy_percentage': evaluation.accuracy_percentage,
                'results': evaluation.results
            }
            
            # Generate PDF
            eval_service = EvaluationService()
            pdf_buffer = eval_service.generate_pdf_report(evaluation_data)
            
            # Create response with PDF
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            filename = f"evaluation_{evaluation.id}_{evaluation.project.title.replace(' ', '_')}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"Generated PDF report for evaluation {evaluation.id}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
            return Response(
                {'error': f'Failed to generate report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_provider_from_model(self, model: str) -> str:
        """Determine provider from model name"""
        model_lower = model.lower()
        
        if 'gpt' in model_lower:
            return 'openai'
        elif 'claude' in model_lower:
            return 'anthropic'
        elif 'gemini' in model_lower:
            return 'google'
        elif 'llama' in model_lower:
            return 'meta'
        
        return 'openai'  # Default
