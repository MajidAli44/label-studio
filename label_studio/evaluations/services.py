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
        Analyzes performance at the individual label level across all tasks
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
            fontSize=22,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=20,
            spaceBefore=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=15,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=10,
            spaceBefore=18,
            fontName='Helvetica-Bold'
        )
        
        subheading_style = ParagraphStyle(
            'SubHeading',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#2c5f2d'),
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        normal_small = ParagraphStyle(
            'NormalSmall',
            parent=styles['Normal'],
            fontSize=9,
            leading=11
        )
        
        # Title
        story.append(Paragraph("Quote Tagging Analysis Report - All Categories Combined", title_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Get evaluation data first
        results = evaluation_data.get('results', {})
        task_evaluations = results.get('task_evaluations', [])
        valid_evals = [e for e in task_evaluations if e.get('evaluated')]
        
        # === LABEL-LEVEL PERFORMANCE ANALYSIS ===
        # Collect performance for each individual label across ALL tasks
        label_performance = {}
        
        for task_eval in valid_evals:
            human_labels = task_eval.get('human_labels', [])
            llm_labels = task_eval.get('llm_labels', [])
            task_id = task_eval.get('task_id', 'Unknown')
            task_inner_id = task_eval.get('task_inner_id', task_id)
            llm_reasoning = task_eval.get('llm_reasoning', '')
            task_content = task_eval.get('task_content', {})
            
            # Get quote_id from task content if available
            quote_id = task_content.get('quote_id', f'Task-{task_inner_id}')
            
            # Convert to sets of tuples for comparison
            human_set = {tuple(label) for label in human_labels}
            llm_set = {tuple(label) for label in llm_labels}
            
            # Get all unique labels from both human and LLM
            all_labels_in_task = human_set | llm_set
            
            for label_tuple in all_labels_in_task:
                label_key = " : ".join(label_tuple)  # e.g., "Priority : High"
                
                if label_key not in label_performance:
                    label_performance[label_key] = {
                        'category': label_tuple[0] if label_tuple else 'Unknown',
                        'value': label_tuple[1] if len(label_tuple) > 1 else '',
                        'true_positives': 0,
                        'false_positives': 0,
                        'false_negatives': 0,
                        'true_negatives': 0,
                        'correctly_selected': [],  # [(quote_id, reasoning)]
                        'incorrectly_selected': [],  # [(quote_id, reasoning)]
                        'missed_selections': [],  # [(quote_id, reasoning)]
                        'llm_assignments': [],  # All LLM assignments with reasoning
                        'human_assignments': []  # All human assignments
                    }
                
                in_human = label_tuple in human_set
                in_llm = label_tuple in llm_set
                
                if in_human and in_llm:
                    # True Positive: Both agree this label applies
                    label_performance[label_key]['true_positives'] += 1
                    label_performance[label_key]['correctly_selected'].append((quote_id, llm_reasoning))
                    label_performance[label_key]['llm_assignments'].append((quote_id, llm_reasoning, 'MATCH'))
                    label_performance[label_key]['human_assignments'].append(quote_id)
                elif not in_human and in_llm:
                    # False Positive: LLM said yes, human said no
                    label_performance[label_key]['false_positives'] += 1
                    label_performance[label_key]['incorrectly_selected'].append((quote_id, llm_reasoning))
                    label_performance[label_key]['llm_assignments'].append((quote_id, llm_reasoning, 'LLM_ONLY'))
                elif in_human and not in_llm:
                    # False Negative: LLM said no, human said yes
                    label_performance[label_key]['false_negatives'] += 1
                    label_performance[label_key]['missed_selections'].append((quote_id, llm_reasoning))
                    label_performance[label_key]['human_assignments'].append(quote_id)
            
            # For True Negatives: labels that were correctly NOT selected
            # We need to consider all possible labels that could have been selected
            # For now, we'll calculate TN based on the labels we've seen
        
        # Calculate True Negatives for each label
        total_tasks = len(valid_evals)
        for label_key, perf in label_performance.items():
            # TN = tasks where neither human nor LLM selected this label
            tasks_with_label = perf['true_positives'] + perf['false_positives'] + perf['false_negatives']
            perf['true_negatives'] = total_tasks - tasks_with_label
        
        # Calculate metrics for all labels (for overall metrics section)
        label_metrics = []
        for label_name, perf_data in label_performance.items():
            tp = perf_data['true_positives']
            fp = perf_data['false_positives']
            fn = perf_data['false_negatives']
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            support = (tp + fn) + (tp + fp)  # Human applied + LLM applied
            jaccard = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
            
            label_metrics.append({
                'f1': f1_score,
                'precision': precision,
                'recall': recall,
                'support': support,
                'jaccard': jaccard
            })
        
        # === OVERALL PERFORMANCE METRICS (ON FIRST PAGE) ===
        story.append(Paragraph("Overall Performance Metrics", heading_style))
        
        # Calculate aggregate statistics
        total_labels = len(label_metrics)
        avg_f1 = sum(m['f1'] for m in label_metrics) / total_labels if total_labels > 0 else 0
        avg_precision = sum(m['precision'] for m in label_metrics) / total_labels if total_labels > 0 else 0
        avg_recall = sum(m['recall'] for m in label_metrics) / total_labels if total_labels > 0 else 0
        
        # Calculate average accuracy across all labels
        total_accuracy = 0
        for label_name, perf_data in label_performance.items():
            tp = perf_data['true_positives']
            fp = perf_data['false_positives']
            fn = perf_data['false_negatives']
            tn = perf_data['true_negatives']
            accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0
            total_accuracy += accuracy
        avg_accuracy = total_accuracy / total_labels if total_labels > 0 else 0
        
        # Count errors (tasks that failed evaluation)
        error_count = len([e for e in task_evaluations if not e.get('evaluated')])
        
        overall_metrics_data = [
            ['Metric', 'Value'],
            ['Project', evaluation_data.get('project_title', 'N/A')],
            ['Total Quotes Processed', str(len(task_evaluations))],
            ['Successful Analyses', str(len(valid_evals))],
            ['Errors', str(error_count)],
            ['Average Accuracy', f"{avg_accuracy:.2%}"],
            ['Average Precision', f"{avg_precision:.2%}"],
            ['Average Recall', f"{avg_recall:.2%}"],
            ['Average F1 Score', f"{avg_f1:.2%}"]
        ]
        
        overall_table = Table(overall_metrics_data, colWidths=[2.8*inch, 3.7*inch])
        overall_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(overall_table)
        story.append(Spacer(1, 0.4*inch))
        
        # === LABEL PERFORMANCE SUMMARY TABLE ===
        story.append(Paragraph("Label Performance Summary (Worst to Best)", heading_style))
        story.append(Paragraph("<i>Priority list for improvement - focus on labels at the top first</i>", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Calculate metrics and sort
        label_summary_data = []
        for label_name, perf_data in label_performance.items():
            tp = perf_data['true_positives']
            fp = perf_data['false_positives']
            fn = perf_data['false_negatives']
            tn = perf_data['true_negatives']
            
            # Key metrics
            human_applied = tp + fn  # How many tasks humans labeled with this
            llm_applied = tp + fp    # How many tasks LLM selected this for
            overlapping = tp         # How many tasks both agreed on
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            # Support and Jaccard
            support = human_applied + llm_applied
            jaccard = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
            
            # Color bucket based on performance metrics only (no support threshold)
            if support == 0:
                color_bucket = "grey"  # No activity at all
            elif f1_score < 0.50 and jaccard < 0.40:
                color_bucket = "red"  # Priority fix needed
            elif (0.50 <= f1_score < 0.80) or (0.40 <= jaccard < 0.70):
                color_bucket = "yellow"  # Needs improvement
            elif f1_score >= 0.80 or jaccard >= 0.70:
                color_bucket = "green"  # Good performance
            else:
                color_bucket = "grey"  # Edge cases with low/unclear performance
            
            label_summary_data.append({
                'label_name': label_name,
                'category': perf_data['category'],
                'f1_score': f1_score,
                'jaccard': jaccard,
                'support': support,
                'human_applied': human_applied,
                'llm_applied': llm_applied,
                'overlapping': overlapping,
                'precision': precision,
                'recall': recall,
                'color_bucket': color_bucket
            })
        
        # Sort by priority
        color_priority = {"red": 1, "yellow": 2, "green": 3, "grey": 4}
        sorted_labels = sorted(
            label_summary_data,
            key=lambda x: (color_priority[x['color_bucket']], -x['support'], -x['f1_score'])
        )
        
        # Create summary table
        summary_table_data = [
            ["Rank", "Label", "Support", "Jaccard", "F1 Score", "Human", "LLM", "Overlap"]
        ]
        
        for rank, data in enumerate(sorted_labels, 1):
            summary_table_data.append([
                str(rank),
                data['label_name'][:40] + ('...' if len(data['label_name']) > 40 else ''),
                str(data['support']),
                f"{data['jaccard']:.2f}",
                f"{data['f1_score']:.2f}",
                str(data['human_applied']),
                str(data['llm_applied']),
                str(data['overlapping'])
            ])
        
        perf_table = Table(
            summary_table_data,
            colWidths=[0.4*inch, 2.3*inch, 0.65*inch, 0.65*inch, 0.7*inch, 0.6*inch, 0.6*inch, 0.7*inch]
        )
        
        # Base styling
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]
        
        # Add row coloring
        for row_idx, data in enumerate(sorted_labels, 1):
            if data['color_bucket'] == "red":
                table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightcoral))
            elif data['color_bucket'] == "yellow":
                table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightyellow))
            elif data['color_bucket'] == "green":
                table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightgreen))
            elif data['color_bucket'] == "grey":
                table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightgrey))
        
        perf_table.setStyle(TableStyle(table_style))
        story.append(perf_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Column Explanations (text format, not table)
        story.append(Paragraph("<b>Column Explanations:</b>", styles['Normal']))
        story.append(Paragraph("<b>Support:</b> Total activity for this label (Human + LLM applications). Low support means insufficient data for reliable metrics.", normal_small))
        story.append(Paragraph("<b>Jaccard:</b> Agreement index = Overlapping / (Human + LLM - Overlapping). Normalized agreement measure that accounts for base rates.", normal_small))
        story.append(Paragraph("<b>F1 Score:</b> Harmonic mean of precision and recall. Balances false positives and false negatives.", normal_small))
        story.append(Paragraph("<b>Human:</b> Number of quotes where human experts applied this label (TP + FN)", normal_small))
        story.append(Paragraph("<b>LLM:</b> Number of quotes where the AI selected this label (TP + FP)", normal_small))
        story.append(Paragraph("<b>Overlap:</b> Number of quotes where both human and AI agreed on this label (TP)", normal_small))
        story.append(Spacer(1, 0.2*inch))
        
        # Priority Guide (text format, not table)
        story.append(Paragraph("<b>Priority Guide (Absolute Performance Thresholds):</b>", styles['Normal']))
        story.append(Paragraph("<b>Red Rows:</b> Priority fix needed - F1 < 0.50 AND Jaccard < 0.40", normal_small))
        story.append(Paragraph("<b>Yellow Rows:</b> Needs improvement - 0.50 <= F1 < 0.80 OR 0.40 <= Jaccard < 0.70", normal_small))
        story.append(Paragraph("<b>Green Rows:</b> Good performance - F1 >= 0.80 OR Jaccard >= 0.70", normal_small))
        story.append(Paragraph("<b>Grey Rows:</b> No activity - Support = 0 (no assignments made)", normal_small))
        story.append(Spacer(1, 0.5*inch))
        
        # === DETAILED LABEL-WISE ANALYSIS ===
        story.append(PageBreak())
        story.append(Paragraph("Tag-Wise Performance Analysis", title_style))
        story.append(Paragraph("<i>Showing ALL labels, including those with minimal assignments</i>", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        current_category = None
        labels_analyzed = 0
        
        for label_data in sorted_labels:
            label_name = label_data['label_name']
            
            # DON'T SKIP - Show all labels regardless of support
            labels_analyzed += 1
            perf = label_performance[label_name]
            
            # Category header
            if current_category != label_data['category']:
                current_category = label_data['category']
                story.append(Paragraph(f"Category: {current_category}", heading_style))
            
            # Label header
            story.append(Paragraph(f"Tag {labels_analyzed}: {label_name}", subheading_style))
            
            # Summary stats for this label
            tp = perf['true_positives']
            fp = perf['false_positives']
            fn = perf['false_negatives']
            tn = perf['true_negatives']
            
            total_llm_assigned = tp + fp
            total_human_assigned = tp + fn
            both_agreed = tp
            
            # Metrics table (removed summary text box)
            precision = label_data['precision']
            recall = label_data['recall']
            f1 = label_data['f1_score']
            accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0
            
            metrics_data = [
                ["Metric", "Value", "Interpretation"],
                ["Precision", f"{precision:.2%}", f"Of {total_llm_assigned} LLM assignments, {tp} were correct"],
                ["Recall", f"{recall:.2%}", f"Of {total_human_assigned} human labels, {tp} were caught by LLM"],
                ["F1 Score", f"{f1:.2%}", "Overall performance balance"],
                ["Accuracy", f"{accuracy:.2%}", f"{tp + tn} correct out of {tp + tn + fp + fn} total decisions"]
            ]
            
            metrics_table = Table(metrics_data, colWidths=[1.2*inch, 1*inch, 4.3*inch])
            bg_color = colors.lightgreen if f1 > 0.8 else colors.lightyellow if f1 > 0.6 else colors.lightcoral
            
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5f2d')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, -1), bg_color),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(metrics_table)
            story.append(Spacer(1, 0.3*inch))
            
            # === DETAILED PERFORMANCE ANALYSIS ===
            story.append(Paragraph("<b>Detailed Performance Analysis:</b>", subheading_style))
            
            # 1. Correctly Selected (True Positives - where both LLM and Human agreed)
            correctly_selected_count = len(perf['correctly_selected'])
            if correctly_selected_count > 0:
                story.append(Paragraph(f"<font color='green'>✓ Correctly Selected ({correctly_selected_count}):</font>", normal_small))
                for idx, (quote_id, reasoning) in enumerate(perf['correctly_selected'], 1):
                    analysis_text = f"<b>• QUO{quote_id}:</b> According to the rule definition: {reasoning[:200] + ('...' if len(reasoning) > 200 else '')}"
                    story.append(Paragraph(analysis_text, normal_small))
                    if idx < correctly_selected_count:
                        story.append(Spacer(1, 0.05*inch))
            else:
                story.append(Paragraph("<font color='green'>✓ Correctly Selected:</font> None", normal_small))
            
            story.append(Spacer(1, 0.15*inch))
            
            # 2. Incorrectly Selected (False Positives - LLM assigned but Human didn't)
            incorrectly_selected_count = len(perf['incorrectly_selected'])
            if incorrectly_selected_count > 0:
                story.append(Paragraph(f"<font color='red'>✗ Incorrectly Selected ({incorrectly_selected_count}):</font>", normal_small))
                for idx, (quote_id, reasoning) in enumerate(perf['incorrectly_selected'], 1):
                    analysis_text = f"<b>• QUO{quote_id}:</b> {reasoning[:200] + ('...' if len(reasoning) > 200 else '')}"
                    story.append(Paragraph(analysis_text, normal_small))
                    if idx < incorrectly_selected_count:
                        story.append(Spacer(1, 0.05*inch))
            else:
                story.append(Paragraph("<font color='red'>✗ Incorrectly Selected:</font> None", normal_small))
            
            story.append(Spacer(1, 0.15*inch))
            
            # 3. Missed Selections (False Negatives - Human assigned but LLM didn't)
            missed_selections_count = len(perf['missed_selections'])
            if missed_selections_count > 0:
                story.append(Paragraph(f"<font color='orange'>■ Missed Selections ({missed_selections_count}):</font>", normal_small))
                for idx, (quote_id, reasoning) in enumerate(perf['missed_selections'], 1):
                    # For missed selections, we show the quote ID that human labeled but LLM missed
                    analysis_text = f"<b>• QUO{quote_id}:</b> According to the rule definition, this quote should have been tagged but LLM did not detect it."
                    story.append(Paragraph(analysis_text, normal_small))
                    if idx < missed_selections_count:
                        story.append(Spacer(1, 0.05*inch))
            else:
                story.append(Paragraph("<font color='orange'>■ Missed Selections:</font> None", normal_small))
            
            story.append(Spacer(1, 0.3*inch))
            
            # === SHORT COMPARISON SUMMARY ===
            story.append(Paragraph("<b>📊 Short Comparison Summary:</b>", subheading_style))
            
            comparison_summary = []
            
            if both_agreed > 0:
                agreement_rate = (both_agreed / total_human_assigned * 100) if total_human_assigned > 0 else 0
                comparison_summary.append(f"• <b>Agreement:</b> {both_agreed} quotes where both LLM and human agreed ({agreement_rate:.1f}% of human assignments)")
            
            if fp > 0:
                comparison_summary.append(f"• <b>Over-selection:</b> LLM assigned this label to {fp} quotes that humans didn't label this way. Review LLM reasoning above to identify patterns in over-selection.")
            
            if fn > 0:
                comparison_summary.append(f"• <b>Under-selection:</b> LLM missed this label on {fn} quotes that humans labeled. This suggests LLM may need clearer criteria or examples.")
            
            if precision < 0.7:
                comparison_summary.append(f"• <b>Precision Issue:</b> Only {precision:.1%} of LLM's {total_llm_assigned} assignments were correct. LLM is being too liberal with this label.")
            
            if recall < 0.7:
                comparison_summary.append(f"• <b>Recall Issue:</b> LLM only caught {recall:.1%} of the {total_human_assigned} human labels. LLM is being too conservative or missing key indicators.")
            
            if f1 >= 0.8:
                comparison_summary.append(f"• <b>Strong Performance:</b> F1 score of {f1:.1%} indicates this label is well-understood by the LLM.")
            elif f1 >= 0.6:
                comparison_summary.append(f"• <b>Moderate Performance:</b> F1 score of {f1:.1%} suggests room for improvement in rule clarity or LLM prompting.")
            else:
                comparison_summary.append(f"• <b>Weak Performance:</b> F1 score of {f1:.1%} indicates significant issues. Review rule definition and LLM reasoning patterns urgently.")
            
            for summary_point in comparison_summary:
                story.append(Paragraph(summary_point, normal_small))
            
            story.append(Spacer(1, 0.3*inch))
            
            # === LLM JUDGE - RULE IMPROVEMENT RECOMMENDATIONS ===
            if f1 < 0.80 or (fp > 0 and fp / (tp + fp) > 0.2):  # Show recommendations for labels with issues
                story.append(Paragraph("■ <b>LLM Judge - Rule Improvement Recommendations:</b>", subheading_style))
                
                recommendations = []
                
                # Analyze patterns and provide specific recommendations
                if precision < 0.70 and fp > 0:
                    recommendations.append(
                        f"<b>**Rule Clarity Issues:**</b> The LLM assigned this label to {fp} quotes that humans didn't select, "
                        f"indicating the rule lacks specificity. The current rule is ambiguous and needs clearer criteria. "
                        f"Review the {fp} false positive cases to identify common patterns where the LLM over-applies this label."
                    )
                
                if recall < 0.70 and fn > 0:
                    recommendations.append(
                        f"<b>**Common Mistakes:**</b> The LLM missed this label on {fn} quotes that humans correctly identified. "
                        f"This suggests the rule definition doesn't effectively guide the AI. Add more specific indicators or examples "
                        f"that help the LLM recognize when this label should be applied."
                    )
                
                if total_llm_assigned > total_human_assigned * 1.5:
                    recommendations.append(
                        f"<b>**Over-application Pattern:**</b> LLM assigned this label {total_llm_assigned} times vs human's {total_human_assigned} times. "
                        f"The rule may be too broad. Consider adding exclusion criteria or threshold requirements to make the rule more selective."
                    )
                
                if total_llm_assigned < total_human_assigned * 0.5:
                    recommendations.append(
                        f"<b>**Under-application Pattern:**</b> LLM only assigned this label {total_llm_assigned} times vs human's {total_human_assigned} times. "
                        f"The rule may be too restrictive or unclear. Consider adding more inclusive examples and clearer positive indicators."
                    )
                
                # Specific improvements based on the data
                if fp > 0:
                    recommendations.append(
                        f"<b>**Specific Improvements:**</b> "
                        f"1. <b>Define Profitability Threshold:</b> Review the {fp} false positive cases and establish clear numeric thresholds. "
                        f"2. <b>Simplify Rule Scope:</b> Focus the rule on specific criteria to avoid confusion with other labels. "
                        f"3. <b>Add Contextual Indicators:</b> Include examples of edge cases to help the AI distinguish true positives from false positives. "
                        f"4. <b>Clarify Exclusions:</b> Specify conditions that do NOT qualify for this label."
                    )
                
                if fn > 0 and recall < 0.70:
                    recommendations.append(
                        f"<b>**Additional Guidance:**</b> Include examples of both correctly and incorrectly tagged instances with explanations. "
                        f"For the {fn} missed cases, provide specific quotes showing why they should have been labeled, "
                        f"helping the LLM understand subtle indicators."
                    )
                
                if not recommendations:
                    recommendations.append(
                        "<b>**Minor Refinements:**</b> Performance is good but can be improved. "
                        "Review edge cases and add more specific examples to push F1 score above 0.80."
                    )
                
                for recommendation in recommendations:
                    story.append(Paragraph(recommendation, normal_small))
                    story.append(Spacer(1, 0.1*inch))
                
                story.append(Spacer(1, 0.2*inch))
            
            story.append(Spacer(1, 0.4*inch))
        
        # Final summary
        story.append(PageBreak())
        story.append(Paragraph("Report Summary", heading_style))
        story.append(Paragraph(f"<b>Total Labels Analyzed:</b> {labels_analyzed}", styles['Normal']))
        story.append(Paragraph(f"<b>Total Tasks Evaluated:</b> {len(valid_evals)}", styles['Normal']))
        story.append(Paragraph(f"<i>All labels are included in this report, regardless of how many times they were assigned.</i>", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _format_labels_for_pdf(self, labels: List[List[str]]) -> str:
        """Format taxonomy labels for PDF display"""
        if not labels:
            return "None"
        return ", ".join([" > ".join(label) for label in labels])
