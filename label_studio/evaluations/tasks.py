"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import logging
from django.db import transaction
from evaluations.models import Evaluation
from evaluations.services import EvaluationService
from projects.models import Project
from tasks.models import Task

logger = logging.getLogger(__name__)


def run_evaluation_async(evaluation_id: int):
    """
    Run evaluation asynchronously
    This can be wrapped with celery/RQ for true async processing
    For now, it runs synchronously but can be easily adapted
    """
    try:
        evaluation = Evaluation.objects.select_related('project').get(id=evaluation_id)
    except Evaluation.DoesNotExist:
        logger.error(f"Evaluation {evaluation_id} not found")
        return
    
    # Mark as running
    evaluation.mark_as_running()
    
    try:
        # Initialize service
        eval_service = EvaluationService()
        
        # Decrypt API key
        api_key = eval_service.decrypt_api_key(evaluation.api_key_encrypted)
        
        # Get project label config and parse taxonomy structure
        taxonomy_structure = None
        if evaluation.project.label_config:
            taxonomy_structure = eval_service.parse_taxonomy_from_config(
                evaluation.project.label_config
            )
            logger.info(f"Parsed taxonomy structure: {taxonomy_structure}")
        
        # Get project tasks
        tasks = Task.objects.filter(
            project=evaluation.project
        ).prefetch_related('annotations')
        
        total_tasks = tasks.count()
        
        if total_tasks == 0:
            evaluation.mark_as_failed("Project has no tasks to evaluate")
            return
        
        # Separate labeled and unlabeled tasks
        labeled_tasks = []
        unlabeled_tasks = []
        
        for task in tasks:
            annotations = list(task.annotations.filter(was_cancelled=False))
            if annotations:
                labeled_tasks.append((task, annotations))
            else:
                unlabeled_tasks.append(task)
        
        labeled_count = len(labeled_tasks)
        
        # If only_labeled_tasks is True, check if we have labeled tasks
        if evaluation.only_labeled_tasks:
            if labeled_count == 0:
                evaluation.mark_as_failed("Project has no labeled tasks to evaluate")
                return
            # Only evaluate labeled tasks
            tasks_to_evaluate = labeled_tasks
        else:
            # Evaluate all tasks (both labeled and unlabeled)
            tasks_to_evaluate = labeled_tasks + [(task, []) for task in unlabeled_tasks]
        
        # Evaluate tasks based on configuration
        results = {
            'task_evaluations': [],
            'summary': {
                'total_tasks': total_tasks,
                'labeled_tasks': labeled_count,
                'unlabeled_tasks': len(unlabeled_tasks),
                'evaluated_tasks': len(tasks_to_evaluate),
                'correct': 0,
                'incorrect': 0,
                'llm_only_labels': 0,
                'errors': 0
            }
        }
        
        for task, annotations in tasks_to_evaluate:
            try:
                task_result = eval_service.evaluate_task(
                    provider=evaluation.model_provider,
                    model=evaluation.llm_model,
                    api_key=api_key,
                    system_prompt=evaluation.system_prompt,
                    task_data=task.data,
                    task_annotations=[ 
                        {
                            'created_at': ann.created_at.isoformat() if ann.created_at else None,
                            'was_cancelled': ann.was_cancelled,
                            'result': ann.result
                        }
                        for ann in annotations
                    ],
                    taxonomy_structure=taxonomy_structure
                )
                
                # Add task ID and details
                task_result['task_id'] = task.id
                task_result['task_inner_id'] = task.inner_id if hasattr(task, 'inner_id') else None
                
                results['task_evaluations'].append(task_result)
                
                # Update summary - use agreement_score for taxonomy-based evaluation
                if task_result.get('evaluated'):
                    has_human_labels = task_result.get('has_human_labels', False)
                    
                    if has_human_labels:
                        # Task has human labels - compare LLM vs human
                        agreement_score = task_result.get('agreement_score', 0)
                        # Consider > 80% agreement as "correct"
                        if agreement_score >= 80:
                            results['summary']['correct'] += 1
                        elif agreement_score > 0:
                            results['summary']['incorrect'] += 1
                        else:
                            results['summary']['incorrect'] += 1
                    else:
                        # Task has no human labels - LLM generated labels only
                        results['summary']['llm_only_labels'] += 1
                else:
                    results['summary']['errors'] += 1
                    
            except Exception as e:
                logger.error(f"Error evaluating task {task.id}: {str(e)}")
                results['task_evaluations'].append({
                    'task_id': task.id,
                    'error': str(e),
                    'evaluated': False
                })
                results['summary']['errors'] += 1
        
        # Update evaluation with results
        evaluation.total_tasks = total_tasks
        evaluation.labeled_tasks = labeled_count
        evaluation.correct_labels = results['summary']['correct']
        evaluation.incorrect_labels = results['summary']['incorrect']
        
        evaluation.mark_as_completed(results)
        
        logger.info(f"Evaluation {evaluation_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Evaluation {evaluation_id} failed: {str(e)}")
        evaluation.mark_as_failed(str(e))


def run_evaluation_sync(evaluation_id: int):
    """
    Synchronous wrapper for running evaluation
    """
    run_evaluation_async(evaluation_id)
