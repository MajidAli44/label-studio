"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import logging
import json
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from cryptography.fernet import Fernet
from django.conf import settings
import requests
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime

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
    
    def parse_taxonomy_from_config(self, label_config: str) -> Dict[str, List[Dict]]:
        """
        Parse taxonomy structure from Label Studio XML config
        Returns: Dict with taxonomy categories and their choices
        """
        try:
            root = ET.fromstring(label_config)
            taxonomies = {}
            
            # Find all Taxonomy elements
            for taxonomy in root.findall('.//Taxonomy'):
                taxonomy_name = taxonomy.get('name', 'taxonomy')
                choices_data = []
                
                # Parse nested Choice elements
                def parse_choice(choice_elem, parent_path=[]):
                    choice_value = choice_elem.get('value', '')
                    choice_hint = choice_elem.get('hint', '')
                    current_path = parent_path + [choice_value]
                    
                    # Check if this choice has nested choices
                    nested_choices = choice_elem.findall('./Choice')
                    
                    if nested_choices:
                        # This is a parent category
                        for nested in nested_choices:
                            parse_choice(nested, current_path)
                    else:
                        # This is a leaf node - add the complete path
                        choices_data.append({
                            'path': current_path,
                            'hint': choice_hint,
                            'category': parent_path[0] if parent_path else choice_value,
                            'value': choice_value
                        })
                
                # Start parsing from top-level choices
                for choice in taxonomy.findall('./Choice'):
                    parse_choice(choice)
                
                taxonomies[taxonomy_name] = choices_data
            
            return taxonomies
            
        except Exception as e:
            logger.error(f"Error parsing taxonomy config: {str(e)}")
            return {}
    
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
        task_annotations: List[Dict],
        taxonomy_structure: Dict = None
    ) -> Dict:
        """
        Evaluate a single task using LLM with auto-labeling
        1. First, ask LLM to assign labels based on taxonomy
        2. Then compare LLM labels with human labels
        Returns: evaluation result with both label sets and comparison
        """
        try:
            # Extract task content (only data, not annotations)
            task_content = task_data
            
            # Get existing human labels if any
            human_labels = self._extract_taxonomy_from_annotations(task_annotations)
            
            # Step 1: Ask LLM to assign labels based on taxonomy structure
            llm_result = self._get_llm_labels(
                provider,
                model,
                api_key,
                system_prompt,
                task_content,
                taxonomy_structure
            )
            
            llm_labels = llm_result.get('labels', [])
            llm_reasoning = llm_result.get('reasoning', '')
            
            # Step 2: Compare human labels with LLM labels
            comparison = self._compare_taxonomy_labels(human_labels, llm_labels)
            
            return {
                'evaluated': True,
                'task_content': task_content,
                'human_labels': human_labels,
                'llm_labels': llm_labels,
                'llm_reasoning': llm_reasoning,
                'comparison': comparison,
                'has_human_labels': len(human_labels) > 0,
                'agreement_score': comparison.get('agreement_percentage', 0)
            }
            
        except Exception as e:
            logger.error(f"Task evaluation error: {str(e)}")
            return {
                'error': str(e),
                'evaluated': False
            }
    
    def _get_llm_labels(
        self,
        provider: str,
        model: str,
        api_key: str,
        system_prompt: str,
        task_content: Dict,
        taxonomy_structure: Dict
    ) -> Dict:
        """
        Ask LLM to assign taxonomy labels to the task
        Returns: Dict with 'labels' and 'reasoning'
        """
        try:
            # Build prompt with task content and available taxonomy options
            labeling_prompt = self._create_labeling_prompt(
                system_prompt,
                task_content,
                taxonomy_structure
            )
            
            # Call LLM API
            llm_response = self._call_llm_api(provider, model, api_key, labeling_prompt)
            
            # Parse LLM response to extract taxonomy paths
            result = self._parse_llm_label_response(llm_response, taxonomy_structure)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting LLM labels: {str(e)}")
            return {'labels': [], 'reasoning': f"Error: {str(e)}"}
    
    def _create_labeling_prompt(
        self,
        system_prompt: str,
        task_content: Dict,
        taxonomy_structure: Dict
    ) -> str:
        """Create prompt for LLM to assign labels"""
        
        # Format task content
        content_text = json.dumps(task_content, indent=2)
        
        # Format available taxonomy options
        taxonomy_options = []
        if taxonomy_structure:
            for tax_name, choices in taxonomy_structure.items():
                taxonomy_options.append(f"\n**{tax_name} Categories:**")
                
                # Group by parent category
                categories = {}
                for choice in choices:
                    parent = choice['category']
                    if parent not in categories:
                        categories[parent] = []
                    categories[parent].append({
                        'value': choice['value'],
                        'hint': choice['hint'],
                        'path': choice['path']
                    })
                
                for category, options in categories.items():
                    taxonomy_options.append(f"\n{category}:")
                    for opt in options:
                        hint_text = f" - {opt['hint']}" if opt['hint'] else ""
                        taxonomy_options.append(f"  - {opt['value']}{hint_text}")
        
        taxonomy_text = "\n".join(taxonomy_options)
        
        prompt = f"""{system_prompt}

**Task Data:**
{content_text}

**Available Taxonomy Labels:**
{taxonomy_text}

**Instructions:**
Analyze the task data above and assign appropriate taxonomy labels from the available options.
Return your labels in this exact JSON format:
{{
  "labels": [
    ["Category1", "Value1"],
    ["Category2", "Value2"]
  ],
  "reasoning": "Brief explanation of why you chose these labels"
}}

Select ALL relevant labels that apply to this task data."""

        return prompt
    
    def _parse_llm_label_response(
        self,
        llm_response: str,
        taxonomy_structure: Dict
    ) -> Dict:
        """Parse LLM response to extract taxonomy labels"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*"labels"[\s\S]*\}', llm_response)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    'labels': data.get('labels', []),
                    'reasoning': data.get('reasoning', '')
                }
            
            # Fallback: try to extract label patterns manually
            labels = []
            lines = llm_response.split('\n')
            for line in lines:
                # Look for patterns like ["Priority", "High"] or [Priority, High]
                matches = re.findall(r'\[(["\']?)([^"\',]+)\1,\s*(["\']?)([^"\',]+)\3\]', line)
                for match in matches:
                    labels.append([match[1].strip(), match[3].strip()])
            
            return {
                'labels': labels,
                'reasoning': llm_response[:200]  # First 200 chars as reasoning
            }
            
        except Exception as e:
            logger.error(f"Error parsing LLM labels: {str(e)}")
            return {'labels': [], 'reasoning': f"Parse error: {str(e)}"}
    
    def _extract_taxonomy_from_annotations(self, annotations: List[Dict]) -> List[List[str]]:
        """Extract taxonomy labels from human annotations"""
        if not annotations:
            return []
        
        # Get the most recent completed annotation
        for annotation in sorted(annotations, key=lambda x: x.get('created_at', ''), reverse=True):
            if annotation.get('was_cancelled'):
                continue
                
            result = annotation.get('result', [])
            for item in result:
                if item.get('type') == 'taxonomy' and 'value' in item:
                    value = item['value']
                    if 'taxonomy' in value:
                        return value['taxonomy']  # Returns list of taxonomy paths
        
        return []
    
    def _compare_taxonomy_labels(
        self,
        human_labels: List[List[str]],
        llm_labels: List[List[str]]
    ) -> Dict:
        """
        Compare human-assigned labels with LLM-assigned labels
        Returns detailed comparison metrics
        """
        # Convert to sets for easier comparison
        human_set = {tuple(label) for label in human_labels}
        llm_set = {tuple(label) for label in llm_labels}
        
        # Find matches and differences
        matching = human_set & llm_set
        human_only = human_set - llm_set
        llm_only = llm_set - human_set
        
        # Calculate metrics
        total_human = len(human_set)
        total_llm = len(llm_set)
        total_unique = len(human_set | llm_set)
        matching_count = len(matching)
        
        agreement_percentage = (matching_count / total_unique * 100) if total_unique > 0 else 0
        
        return {
            'matching_labels': [list(label) for label in matching],
            'human_only_labels': [list(label) for label in human_only],
            'llm_only_labels': [list(label) for label in llm_only],
            'total_human_labels': total_human,
            'total_llm_labels': total_llm,
            'matching_count': matching_count,
            'agreement_percentage': round(agreement_percentage, 2),
            'perfect_match': human_set == llm_set
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
    
    def generate_pdf_report(self, evaluation_data: Dict) -> BytesIO:
        """
        Generate a comprehensive PDF report for the evaluation
        Returns: BytesIO buffer with PDF content
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1890ff'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#262626'),
            spaceAfter=12,
            spaceBefore=20
        )
        
        # Title
        story.append(Paragraph("LLM Label Evaluation Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Evaluation metadata
        metadata = [
            ['Project:', evaluation_data.get('project_title', 'N/A')],
            ['Model:', evaluation_data.get('llm_model', 'N/A')],
            ['Date:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Status:', evaluation_data.get('status', 'N/A')]
        ]
        
        meta_table = Table(metadata, colWidths=[2*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Summary statistics
        story.append(Paragraph("Summary Statistics", heading_style))
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Tasks', str(evaluation_data.get('total_tasks', 0))],
            ['Labeled Tasks', str(evaluation_data.get('labeled_tasks', 0))],
            ['Overall Agreement', f"{evaluation_data.get('accuracy_percentage', 0):.2f}%"],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1890ff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 12),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Detailed task results
        story.append(Paragraph("Detailed Task Results", heading_style))
        
        results = evaluation_data.get('results', {})
        task_evaluations = results.get('task_evaluations', [])
        
        for idx, task_eval in enumerate(task_evaluations, 1):
            if not task_eval.get('evaluated'):
                continue
            
            story.append(Paragraph(f"<b>Task {idx}</b>", styles['Heading3']))
            
            # Task content summary
            task_content = task_eval.get('task_content', {})
            text = task_content.get('text', 'N/A')
            story.append(Paragraph(f"<b>Text:</b> {text[:200]}...", styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
            
            # Labels comparison
            human_labels = task_eval.get('human_labels', [])
            llm_labels = task_eval.get('llm_labels', [])
            comparison = task_eval.get('comparison', {})
            
            labels_data = [
                ['Label Type', 'Labels'],
                ['Human Labels', self._format_labels_for_pdf(human_labels)],
                ['LLM Labels', self._format_labels_for_pdf(llm_labels)],
                ['Agreement', f"{comparison.get('agreement_percentage', 0):.1f}%"]
            ]
            
            labels_table = Table(labels_data, colWidths=[2*inch, 4*inch])
            labels_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6f7ff')),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(labels_table)
            
            # Matching/Non-matching details
            matching = comparison.get('matching_labels', [])
            human_only = comparison.get('human_only_labels', [])
            llm_only = comparison.get('llm_only_labels', [])
            
            if matching:
                story.append(Paragraph(f"<font color='green'>✓ Matching: {self._format_labels_for_pdf(matching)}</font>", styles['Normal']))
            if human_only:
                story.append(Paragraph(f"<font color='orange'>⚠ Human Only: {self._format_labels_for_pdf(human_only)}</font>", styles['Normal']))
            if llm_only:
                story.append(Paragraph(f"<font color='blue'>ℹ LLM Only: {self._format_labels_for_pdf(llm_only)}</font>", styles['Normal']))
            
            # LLM Reasoning
            reasoning = task_eval.get('llm_reasoning', '')
            if reasoning:
                story.append(Spacer(1, 0.05*inch))
                story.append(Paragraph(f"<b>LLM Reasoning:</b> {reasoning[:300]}...", styles['Normal']))
            
            story.append(Spacer(1, 0.2*inch))
            
            # Page break after every 3 tasks
            if idx % 3 == 0 and idx < len(task_evaluations):
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _format_labels_for_pdf(self, labels: List[List[str]]) -> str:
        """Format taxonomy labels for PDF display"""
        if not labels:
            return "None"
        return ", ".join([" > ".join(label) for label in labels])
