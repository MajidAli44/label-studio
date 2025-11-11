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
            llm_label = self._extract_label_from_response(llm_response)
            
            # Compare labels
            is_correct = self._compare_labels(existing_label, llm_label) if existing_label else None
            
            return {
                'evaluated': True,
                'task_text': task_text,
                'existing_label': existing_label,
                'llm_label': llm_label,
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
    
    def _extract_label_from_annotations(self, annotations: List[Dict]) -> Optional[str]:
        """Extract label from task annotations"""
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
                        # Handle different label formats
                        if isinstance(value, dict):
                            if 'choices' in value:
                                return ', '.join(value['choices'])
                            elif 'labels' in value:
                                return ', '.join(value['labels'])
                            elif 'text' in value:
                                return value['text']
                        elif isinstance(value, (str, list)):
                            return str(value)
        
        return None
    
    def _create_evaluation_prompt(
        self, 
        system_prompt: str, 
        task_text: str, 
        existing_label: Optional[str]
    ) -> str:
        """Create evaluation prompt for LLM"""
        if existing_label:
            return f"""{system_prompt}

Task Text: {task_text}

Existing Label: {existing_label}

Please evaluate if the existing label is correct for this task. Respond with:
1. Your evaluation of the label (correct/incorrect)
2. What you think the correct label should be
3. Brief explanation of your reasoning"""
        else:
            return f"""{system_prompt}

Task Text: {task_text}

This task has no existing label. Please provide:
1. What label you would assign to this task
2. Brief explanation of your reasoning"""
    
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
    
    def _extract_label_from_response(self, response: str) -> Optional[str]:
        """Extract label from LLM response"""
        # Try to extract structured label
        # Look for patterns like "Label: X" or "Correct label: X"
        patterns = [
            r'(?:correct label|should be|label):\s*["\']?([^"\'\n]+)["\']?',
            r'I would label this as[:\s]+["\']?([^"\'\n]+)["\']?',
            r'The label should be[:\s]+["\']?([^"\'\n]+)["\']?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback: return first line or first 100 chars
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) < 100:
                return line
        
        return response[:100].strip()
    
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
