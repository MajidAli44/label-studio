"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import logging
import json
import re
from typing import Dict, List, Optional, Tuple
from cryptography.fernet import Fernet
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Exception raised for LLM provider errors"""
    pass


class EvaluationService:
    """Service to handle LLM evaluations"""
    
    # Model provider configurations
    PROVIDER_CONFIGS = {
        'openai': {
            'api_url': 'https://api.openai.com/v1/chat/completions',
            'models': ['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo'],
            'headers': lambda key: {
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json'
            }
        },
        'anthropic': {
            'api_url': 'https://api.anthropic.com/v1/messages',
            'models': ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
            'headers': lambda key: {
                'x-api-key': key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            }
        },
        'google': {
            'api_url': 'https://generativelanguage.googleapis.com/v1/models/',
            'models': ['gemini-pro', 'gemini-pro-vision'],
            'headers': lambda key: {
                'Content-Type': 'application/json'
            }
        }
    }
    
    def __init__(self):
        # Initialize encryption key for API keys
        self.cipher_suite = None
        if hasattr(settings, 'SECRET_KEY'):
            # Use Django's SECRET_KEY to derive encryption key
            key = settings.SECRET_KEY.encode()[:32].ljust(32, b'0')
            from base64 import urlsafe_b64encode
            self.cipher_suite = Fernet(urlsafe_b64encode(key))
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for storage"""
        if not self.cipher_suite:
            return api_key  # Fallback if encryption not available
        return self.cipher_suite.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key for use"""
        if not self.cipher_suite:
            return encrypted_key  # Fallback if encryption not available
        return self.cipher_suite.decrypt(encrypted_key.encode()).decode()
    
    def validate_api_key(self, provider: str, api_key: str, model: str) -> Tuple[bool, Optional[str]]:
        """
        Validate API key by making a test request
        Returns: (is_valid, error_message)
        """
        try:
            config = self.PROVIDER_CONFIGS.get(provider.lower())
            if not config:
                return False, f"Unsupported provider: {provider}"
            
            if model not in config['models']:
                return False, f"Model {model} not supported for provider {provider}"
            
            # Make a simple test request based on provider
            if provider.lower() == 'openai':
                return self._validate_openai_key(api_key, model, config)
            elif provider.lower() == 'anthropic':
                return self._validate_anthropic_key(api_key, model, config)
            elif provider.lower() == 'google':
                return self._validate_google_key(api_key, model, config)
            
            return False, "Provider validation not implemented"
            
        except Exception as e:
            logger.error(f"API key validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    def _validate_openai_key(self, api_key: str, model: str, config: Dict) -> Tuple[bool, Optional[str]]:
        """Validate OpenAI API key"""
        try:
            response = requests.post(
                config['api_url'],
                headers=config['headers'](api_key),
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 5
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return True, None
            elif response.status_code == 401:
                return False, "Invalid API key"
            else:
                return False, f"API error: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Connection error: {str(e)}"
    
    def _validate_anthropic_key(self, api_key: str, model: str, config: Dict) -> Tuple[bool, Optional[str]]:
        """Validate Anthropic API key"""
        try:
            response = requests.post(
                config['api_url'],
                headers=config['headers'](api_key),
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 5
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return True, None
            elif response.status_code == 401:
                return False, "Invalid API key"
            else:
                return False, f"API error: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Connection error: {str(e)}"
    
    def _validate_google_key(self, api_key: str, model: str, config: Dict) -> Tuple[bool, Optional[str]]:
        """Validate Google API key"""
        try:
            url = f"{config['api_url']}{model}:generateContent?key={api_key}"
            response = requests.post(
                url,
                headers=config['headers'](api_key),
                json={
                    "contents": [{"parts": [{"text": "test"}]}]
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return True, None
            elif response.status_code == 400 and 'API_KEY_INVALID' in response.text:
                return False, "Invalid API key"
            else:
                return False, f"API error: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Connection error: {str(e)}"
    
    def evaluate_task(
        self, 
        provider: str, 
        model: str, 
        api_key: str, 
        system_prompt: str, 
        task_data: Dict,
        task_annotations: List[Dict]
    ) -> Dict:
        """
        Evaluate a single task using LLM
        Returns: evaluation result with LLM response and comparison
        """
        try:
            # Get task text content
            task_text = self._extract_task_text(task_data)
            if not task_text:
                return {
                    'error': 'No text content found in task',
                    'evaluated': False
                }
            
            # Get existing label if any
            existing_label = self._extract_label_from_annotations(task_annotations)
            
            # Create evaluation prompt
            evaluation_prompt = self._create_evaluation_prompt(
                system_prompt, 
                task_text, 
                existing_label
            )
            
            # Call LLM API
            llm_response = self._call_llm_api(
                provider, 
                model, 
                api_key, 
                evaluation_prompt
            )
            
            # Extract LLM's label from response
            llm_evaluation = self._extract_label_from_response(llm_response, existing_label)
            
            # Determine if correct
            is_correct = None
            if existing_label:
                if llm_evaluation.get('type') == 'taxonomy':
                    is_correct = llm_evaluation.get('overall_correct')
                else:
                    is_correct = llm_evaluation.get('is_correct')
            
            return {
                'evaluated': True,
                'task_text': task_text,
                'existing_label': existing_label,
                'llm_evaluation': llm_evaluation,
                'llm_full_response': llm_response,
                'is_correct': is_correct,
                'has_existing_label': existing_label is not None
            }
            
        except Exception as e:
            logger.error(f"Task evaluation error: {str(e)}")
            return {
                'error': str(e),
                'evaluated': False
            }
    
    def _extract_task_text(self, task_data: Dict) -> Optional[str]:
        """Extract text content from task data"""
        # Common text field names
        text_fields = ['text', 'content', 'data', 'input', 'question', 'document']
        
        for field in text_fields:
            if field in task_data:
                value = task_data[field]
                if isinstance(value, str):
                    return value
                elif isinstance(value, dict) and 'text' in value:
                    return value['text']
        
        # Fallback: convert entire data to string if it's small enough
        task_str = json.dumps(task_data)
        if len(task_str) < 10000:
            return task_str
        
        return None
    
    def _extract_label_from_annotations(self, annotations: List[Dict]) -> Optional[Dict]:
        """Extract label from task annotations - returns structured data for taxonomy"""
        if not annotations:
            return None
        
        # Get the most recent completed annotation
        for annotation in sorted(annotations, key=lambda x: x.get('created_at', ''), reverse=True):
            if annotation.get('was_cancelled'):
                continue
                
            result = annotation.get('result', [])
            if result:
                # Extract label from result
                for item in result:
                    if 'value' in item:
                        value = item['value']
                        label_type = item.get('type', 'unknown')
                        
                        # Handle taxonomy labels specifically
                        if label_type == 'taxonomy' and 'taxonomy' in value:
                            taxonomy_labels = value['taxonomy']
                            # Format: [["Priority", "High"], ["Others", "Prices"]]
                            formatted = []
                            for tax in taxonomy_labels:
                                if isinstance(tax, list) and len(tax) >= 2:
                                    formatted.append(f"{tax[0]}: {tax[1]}")
                            return {
                                'type': 'taxonomy',
                                'labels': formatted,
                                'raw': taxonomy_labels
                            }
                        
                        # Handle other label formats
                        elif isinstance(value, dict):
                            if 'choices' in value:
                                return {
                                    'type': 'choices',
                                    'labels': value['choices'],
                                    'raw': value['choices']
                                }
                            elif 'labels' in value:
                                return {
                                    'type': 'labels',
                                    'labels': value['labels'],
                                    'raw': value['labels']
                                }
                            elif 'text' in value:
                                return {
                                    'type': 'text',
                                    'labels': [value['text']],
                                    'raw': value['text']
                                }
                        elif isinstance(value, list):
                            return {
                                'type': 'list',
                                'labels': value,
                                'raw': value
                            }
                        elif isinstance(value, str):
                            return {
                                'type': 'string',
                                'labels': [value],
                                'raw': value
                            }
        
        return None
    
    def _create_evaluation_prompt(
        self, 
        system_prompt: str, 
        task_text: str, 
        existing_label: Optional[Dict]
    ) -> str:
        """Create evaluation prompt for LLM"""
        if existing_label:
            label_type = existing_label.get('type', 'unknown')
            labels = existing_label.get('labels', [])
            
            if label_type == 'taxonomy':
                # Special handling for taxonomy labels
                labels_text = '\n'.join([f"  - {label}" for label in labels])
                return f"""{system_prompt}

Text to analyze:
"{task_text}"

Existing Labels (Taxonomy):
{labels_text}

Task: Evaluate EACH label individually and determine if it correctly classifies the text.
For each label, analyze:
1. Is this category/classification appropriate for the text?
2. Does the text content support this label?

Respond in this format:
Label 1 [{labels[0] if labels else ''}]: CORRECT or INCORRECT - brief reason
Label 2 [{labels[1] if len(labels) > 1 else ''}]: CORRECT or INCORRECT - brief reason
(continue for each label)

Overall Assessment: State if all labels are correct or which ones need changes."""
            else:
                # Other label types
                labels_text = ', '.join(labels)
                return f"""{system_prompt}

Text: "{task_text}"

Existing Label(s): {labels_text}

Evaluate if this label correctly classifies the text. Respond with:
1. CORRECT or INCORRECT
2. Brief explanation
3. If incorrect, suggest the correct label"""
        else:
            return f"""{system_prompt}

Text: "{task_text}"

This text has no existing label. Please:
1. Suggest appropriate label(s)
2. Explain your reasoning"""
    
    def _call_llm_api(
        self, 
        provider: str, 
        model: str, 
        api_key: str, 
        prompt: str
    ) -> str:
        """Call LLM API and return response"""
        config = self.PROVIDER_CONFIGS.get(provider.lower())
        if not config:
            raise LLMProviderError(f"Unsupported provider: {provider}")
        
        if provider.lower() == 'openai':
            return self._call_openai_api(model, api_key, prompt, config)
        elif provider.lower() == 'anthropic':
            return self._call_anthropic_api(model, api_key, prompt, config)
        elif provider.lower() == 'google':
            return self._call_google_api(model, api_key, prompt, config)
        
        raise LLMProviderError("Provider not implemented")
    
    def _call_openai_api(self, model: str, api_key: str, prompt: str, config: Dict) -> str:
        """Call OpenAI API"""
        response = requests.post(
            config['api_url'],
            headers=config['headers'](api_key),
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.3
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise LLMProviderError(f"OpenAI API error: {response.status_code} - {response.text}")
        
        data = response.json()
        return data['choices'][0]['message']['content']
    
    def _call_anthropic_api(self, model: str, api_key: str, prompt: str, config: Dict) -> str:
        """Call Anthropic API"""
        response = requests.post(
            config['api_url'],
            headers=config['headers'](api_key),
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise LLMProviderError(f"Anthropic API error: {response.status_code} - {response.text}")
        
        data = response.json()
        return data['content'][0]['text']
    
    def _call_google_api(self, model: str, api_key: str, prompt: str, config: Dict) -> str:
        """Call Google API"""
        url = f"{config['api_url']}{model}:generateContent?key={api_key}"
        response = requests.post(
            url,
            headers=config['headers'](api_key),
            json={
                "contents": [{"parts": [{"text": prompt}]}]
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise LLMProviderError(f"Google API error: {response.status_code} - {response.text}")
        
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    
    def _extract_label_from_response(self, response: str, existing_label: Optional[Dict] = None) -> Dict:
        """Extract label evaluation from LLM response"""
        response_lower = response.lower()
        
        # For taxonomy labels, parse individual label evaluations
        if existing_label and existing_label.get('type') == 'taxonomy':
            labels = existing_label.get('labels', [])
            evaluations = []
            
            for i, label in enumerate(labels, 1):
                # Look for patterns like "Label 1: CORRECT" or "Priority: High - CORRECT"
                patterns = [
                    rf'label\s*{i}[:\s]+.*?(correct|incorrect)',
                    rf'{re.escape(label)}[:\s]+.*?(correct|incorrect)',
                ]
                
                found = False
                for pattern in patterns:
                    match = re.search(pattern, response_lower)
                    if match:
                        is_correct = match.group(1) == 'correct'
                        evaluations.append({
                            'label': label,
                            'is_correct': is_correct
                        })
                        found = True
                        break
                
                if not found:
                    # Default: check if the label appears near "correct" or "incorrect"
                    label_lower = label.lower()
                    context_before = 50
                    context_after = 50
                    
                    if label_lower in response_lower:
                        idx = response_lower.find(label_lower)
                        context = response_lower[max(0, idx-context_before):idx+len(label_lower)+context_after]
                        
                        if 'correct' in context:
                            if 'incorrect' in context:
                                # If both, check which is closer
                                correct_dist = abs(context.find('correct') - len(label_lower))
                                incorrect_dist = abs(context.find('incorrect') - len(label_lower))
                                is_correct = correct_dist < incorrect_dist
                            else:
                                is_correct = True
                        elif 'incorrect' in context:
                            is_correct = False
                        else:
                            is_correct = None
                        
                        evaluations.append({
                            'label': label,
                            'is_correct': is_correct
                        })
            
            # Determine overall correctness
            if all(e.get('is_correct') == True for e in evaluations if e.get('is_correct') is not None):
                overall_correct = True
            elif any(e.get('is_correct') == False for e in evaluations):
                overall_correct = False
            else:
                overall_correct = None
            
            return {
                'type': 'taxonomy',
                'evaluations': evaluations,
                'overall_correct': overall_correct,
                'full_response': response
            }
        
        # For other label types, simpler evaluation
        else:
            is_correct = None
            if 'correct' in response_lower and 'incorrect' not in response_lower:
                is_correct = True
            elif 'incorrect' in response_lower:
                is_correct = False
            
            return {
                'type': 'simple',
                'is_correct': is_correct,
                'full_response': response
            }
    
    def _compare_labels(self, label1: Optional[str], label2: Optional[str]) -> bool:
        """Compare two labels for similarity"""
        if not label1 or not label2:
            return False
        
        # Normalize labels
        norm1 = label1.lower().strip()
        norm2 = label2.lower().strip()
        
        # Exact match
        if norm1 == norm2:
            return True
        
        # Fuzzy match - check if one contains the other
        if norm1 in norm2 or norm2 in norm1:
            return True
        
        return False
