import React, { useState, useEffect, useContext } from 'react';
import { Button, Spinner } from '@humansignal/ui';
import { useUpdatePageTitle } from '@humansignal/core';
import { ApiContext } from '../../providers/ApiProvider';
import './EvalPage.scss';
import type { Page } from '../types/Page';

const LLM_MODELS = [
  { id: "gpt-4", name: "GPT-4", provider: "OpenAI" },
  { id: "gpt-4-turbo", name: "GPT-4 Turbo", provider: "OpenAI" },
  { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI" },
  { id: "gpt-4o-mini", name: "GPT-4o Mini", provider: "OpenAI" },
  { id: "gpt-3.5-turbo", name: "GPT-3.5 Turbo", provider: "OpenAI" },
];

interface Project {
  id: number;
  title: string;
}

interface Evaluation {
  id: number;
  project_title: string;
  llm_model: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  accuracy_percentage?: number;
  labeled_tasks: number;
  total_tasks: number;
  correct_labels: number;
  incorrect_labels: number;
  error_message?: string;
  results?: any;
}

export const EvalPage = () => {
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [apiKey, setApiKey] = useState<string>("");
  const [systemPrompt, setSystemPrompt] = useState<string>("");
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [currentEvaluation, setCurrentEvaluation] = useState<Evaluation | null>(null);
  const [showResults, setShowResults] = useState<boolean>(false);
  const [useDefaultKey, setUseDefaultKey] = useState<boolean>(true);

  const api = useContext(ApiContext);

  useUpdatePageTitle('Evaluation');

  const MASKED_API_KEY = "sk-proj-...";

  // Fetch projects on component mount
  useEffect(() => {
    const fetchProjects = async () => {
      if (!api) return;
      
      try {
        setLoadingProjects(true);
        const response = await api.callApi<{ results: Project[]; count: number }>("projects", {
          params: {
            page_size: 1000, // Get all projects
            include: "id,title"
          },
        });
        
        if (response?.results) {
          setProjects(response.results);
        }
      } catch (error) {
        console.error("Failed to fetch projects:", error);
      } finally {
        setLoadingProjects(false);
      }
    };

    fetchProjects();
  }, [api]);

  const handleSubmit = async () => {
    if (!selectedModel || !systemPrompt.trim() || !selectedProject) {
      alert("Please fill in all required fields");
      return;
    }

    if (!api) {
      alert("API not available");
      return;
    }

    try {
      setSubmitting(true);
      
      // Create evaluation using direct fetch since API proxy may not have this endpoint yet
      const response = await fetch('/api/evaluations/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          project_id: parseInt(selectedProject),
          llm_model: selectedModel,
          system_prompt: systemPrompt,
          use_default_api_key: useDefaultKey,  // Signal to use server-side default key
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || error.detail || 'Failed to create evaluation');
      }

      const evaluation: Evaluation = await response.json();
      
      setCurrentEvaluation(evaluation);
      setShowResults(true);
      
      // Reset form
      setSelectedModel("");
      setSystemPrompt("");
      setSelectedProject("");
      
      // Poll for results if evaluation is running
      if (evaluation.status === 'pending' || evaluation.status === 'running') {
        pollEvaluationStatus(evaluation.id);
      }
    } catch (error: any) {
      console.error("Failed to create evaluation:", error);
      alert(`Failed to create evaluation: ${error?.message || 'Unknown error'}`);
    } finally {
      setSubmitting(false);
    }
  };

  const pollEvaluationStatus = async (evaluationId: number) => {
    const maxAttempts = 60; // Poll for up to 5 minutes
    let attempts = 0;

    const pollInterval = setInterval(async () => {
      try {
        attempts++;
        
        const response = await fetch(`/api/evaluations/${evaluationId}/`, {
          credentials: 'include',
        });
        
        if (response.ok) {
          const evaluation: Evaluation = await response.json();
          setCurrentEvaluation(evaluation);
          
          // Stop polling if completed or failed
          if (evaluation.status === 'completed' || evaluation.status === 'failed') {
            clearInterval(pollInterval);
          }
        }

        // Stop after max attempts
        if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error("Failed to poll evaluation status:", error);
        clearInterval(pollInterval);
      }
    }, 5000); // Poll every 5 seconds
  };

  // Form is valid if we have model, prompt, project, and either using default key or have custom key
  const isFormValid = selectedModel && systemPrompt.trim() && selectedProject && (useDefaultKey || apiKey.trim());

  return (
    <div className="eval-page" style={{ padding: '40px 48px', maxWidth: '1200px', margin: '0 auto', minHeight: '100vh', background: '#f5f5f5' }}>
      <div className="eval-page__header" style={{ marginBottom: '32px', paddingBottom: '24px', borderBottom: '2px solid #e8e8e8' }}>
        <h1 className="eval-page__title" style={{ fontSize: '32px', fontWeight: 700, color: '#1a1a1a', margin: '0 0 12px 0', letterSpacing: '-0.03em' }}>LLM Model Evaluation</h1>
        <p className="eval-page__subtitle" style={{ fontSize: '16px', color: '#666', margin: '0', lineHeight: 1.6 }}>
          Configure and run evaluations on your language models. Test different models, prompts, and datasets to compare performance.
        </p>
      </div>

      <div className="eval-page__form-container" style={{ background: '#ffffff', border: '1px solid #e0e0e0', borderRadius: '12px', padding: '48px', boxShadow: '0 4px 16px rgba(0, 0, 0, 0.06)' }}>
        <div className="eval-page__form" style={{ maxWidth: '700px', margin: '0 auto' }}>
          {/* Field 1: Select LLM Model */}
          <div className="eval-page__field" style={{ marginBottom: '36px' }}>
            <label className="eval-page__label" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px', fontSize: '16px', fontWeight: 600, color: '#1a1a1a' }}>
              <span className="eval-page__label-number" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '32px', height: '32px', background: 'linear-gradient(135deg, #1890ff 0%, #0066cc 100%)', color: 'white', borderRadius: '50%', fontSize: '14px', fontWeight: 700, flexShrink: 0, boxShadow: '0 3px 8px rgba(24, 144, 255, 0.35)' }}>1</span>
              <span className="eval-page__label-text" style={{ flex: 1, fontSize: '16px' }}>Select LLM Model</span>
              <span className="eval-page__label-required" style={{ color: '#ff4d4f', fontSize: '20px', fontWeight: 700, marginLeft: '4px' }}>*</span>
            </label>
            <select
              className="eval-page__input eval-page__select"
              style={{ 
                width: '100%', 
                padding: '14px 18px', 
                paddingRight: '50px',
                border: '2px solid #d9d9d9', 
                borderRadius: '8px', 
                fontSize: '15px', 
                fontFamily: 'inherit', 
                color: '#262626', 
                background: '#fafafa',
                cursor: 'pointer',
                appearance: 'none',
                backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%23595959' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E\")",
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 16px center',
                backgroundSize: '18px'
              }}
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              <option value="">Choose an LLM model for evaluation</option>
              {LLM_MODELS.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name} ({model.provider})
                </option>
              ))}
            </select>
          </div>

          {/* Field 2: Enter API Key */}
          <div className="eval-page__field" style={{ marginBottom: '36px' }}>
            <label className="eval-page__label" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px', fontSize: '16px', fontWeight: 600, color: '#1a1a1a' }}>
              <span className="eval-page__label-number" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '32px', height: '32px', background: 'linear-gradient(135deg, #1890ff 0%, #0066cc 100%)', color: 'white', borderRadius: '50%', fontSize: '14px', fontWeight: 700, flexShrink: 0, boxShadow: '0 3px 8px rgba(24, 144, 255, 0.35)' }}>2</span>
              <span className="eval-page__label-text" style={{ flex: 1, fontSize: '16px' }}>API Key</span>
            </label>
            <input
              type="text"
              className="eval-page__input"
              style={{
                width: '100%',
                padding: '14px 18px',
                border: '2px solid #d9d9d9',
                borderRadius: '8px',
                fontSize: '15px',
                fontFamily: 'monospace',
                color: '#8c8c8c',
                background: '#fafafa',
                transition: 'all 0.25s ease',
                boxSizing: 'border-box',
                cursor: 'not-allowed'
              }}
              value={MASKED_API_KEY}
              readOnly
              disabled
            />
            <div className="eval-page__help-text" style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', marginTop: '10px', padding: '12px 14px', background: '#f0f7ff', borderRadius: '6px', fontSize: '13px', color: '#595959', lineHeight: 1.6 }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, color: '#1890ff', marginTop: '2px' }}>
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
              <span>Default API key is pre-configured and secured</span>
            </div>
          </div>

          {/* Field 3: Enter System Prompt */}
          <div className="eval-page__field" style={{ marginBottom: '36px' }}>
            <label className="eval-page__label" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px', fontSize: '16px', fontWeight: 600, color: '#1a1a1a' }}>
              <span className="eval-page__label-number" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '32px', height: '32px', background: 'linear-gradient(135deg, #1890ff 0%, #0066cc 100%)', color: 'white', borderRadius: '50%', fontSize: '14px', fontWeight: 700, flexShrink: 0, boxShadow: '0 3px 8px rgba(24, 144, 255, 0.35)' }}>3</span>
              <span className="eval-page__label-text" style={{ flex: 1, fontSize: '16px' }}>Enter System Prompt</span>
              <span className="eval-page__label-required" style={{ color: '#ff4d4f', fontSize: '20px', fontWeight: 700, marginLeft: '4px' }}>*</span>
            </label>
            <textarea
              className="eval-page__input eval-page__textarea"
              style={{
                width: '100%',
                minHeight: '130px',
                padding: '14px 18px',
                border: '2px solid #d9d9d9',
                borderRadius: '8px',
                fontSize: '15px',
                fontFamily: 'inherit',
                color: '#262626',
                background: '#ffffff',
                transition: 'all 0.25s ease',
                resize: 'vertical',
                lineHeight: 1.65,
                boxSizing: 'border-box'
              }}
              placeholder="You are a helpful assistant that evaluates..."
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={4}
            />
            <div className="eval-page__help-text" style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', marginTop: '10px', padding: '12px 14px', background: '#f7f7f7', borderRadius: '6px', fontSize: '13px', color: '#595959', lineHeight: 1.6 }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, color: '#8c8c8c', marginTop: '2px' }}>
                <circle cx="12" cy="12" r="10"/>
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <span>Define the system behavior and instructions for the LLM evaluation</span>
            </div>
          </div>

          {/* Field 4: Select Project */}
          <div className="eval-page__field" style={{ marginBottom: '36px' }}>
            <label className="eval-page__label" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px', fontSize: '16px', fontWeight: 600, color: '#1a1a1a' }}>
              <span className="eval-page__label-number" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '32px', height: '32px', background: 'linear-gradient(135deg, #1890ff 0%, #0066cc 100%)', color: 'white', borderRadius: '50%', fontSize: '14px', fontWeight: 700, flexShrink: 0, boxShadow: '0 3px 8px rgba(24, 144, 255, 0.35)' }}>4</span>
              <span className="eval-page__label-text" style={{ flex: 1, fontSize: '16px' }}>Select Project</span>
              <span className="eval-page__label-required" style={{ color: '#ff4d4f', fontSize: '20px', fontWeight: 700, marginLeft: '4px' }}>*</span>
            </label>
            
            {loadingProjects ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '14px 18px', border: '2px solid #d9d9d9', borderRadius: '8px', background: '#fafafa' }}>
                <Spinner size={16} />
                <span style={{ fontSize: '15px', color: '#8c8c8c' }}>Loading projects...</span>
              </div>
            ) : (
              <select
                className="eval-page__input eval-page__select"
                style={{ 
                  width: '100%', 
                  padding: '14px 18px', 
                  paddingRight: '50px',
                  border: '2px solid #d9d9d9', 
                  borderRadius: '8px', 
                  fontSize: '15px', 
                  fontFamily: 'inherit', 
                  color: '#262626', 
                  background: '#fafafa',
                  cursor: 'pointer',
                  appearance: 'none',
                  backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%23595959' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E\")",
                  backgroundRepeat: 'no-repeat',
                  backgroundPosition: 'right 16px center',
                  backgroundSize: '18px',
                  boxSizing: 'border-box'
                }}
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
              >
                <option value="">Choose a project for evaluation</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.title}
                  </option>
                ))}
              </select>
            )}
            
            <div className="eval-page__help-text" style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', marginTop: '10px', padding: '12px 14px', background: '#f7f7f7', borderRadius: '6px', fontSize: '13px', color: '#595959', lineHeight: 1.6 }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, color: '#8c8c8c', marginTop: '2px' }}>
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
              <span>Select the project you want to evaluate. All your existing projects are listed here.</span>
            </div>
          </div>

          {/* Submit Button */}
          <div className="eval-page__actions" style={{ marginTop: '48px', paddingTop: '36px', borderTop: '2px solid #e8e8e8', display: 'flex', justifyContent: 'center' }}>
            <Button 
              onClick={handleSubmit} 
              disabled={!isFormValid || submitting}
              style={{ 
                minWidth: '220px', 
                padding: '14px 40px', 
                fontSize: '16px', 
                fontWeight: 600, 
                borderRadius: '8px', 
                transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)', 
                boxShadow: (!isFormValid || submitting) ? 'none' : '0 2px 8px rgba(24, 144, 255, 0.2)',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
              }}
            >
              {submitting && <Spinner size={16} />}
              {submitting ? 'Creating Evaluation...' : 'Create Evaluation'}
            </Button>
          </div>
        </div>
      </div>

      {/* Results Section */}
      {showResults && currentEvaluation && (
        <div style={{ marginTop: '32px', background: '#ffffff', border: '1px solid #e0e0e0', borderRadius: '12px', padding: '32px', boxShadow: '0 4px 16px rgba(0, 0, 0, 0.06)' }}>
          <div style={{ marginBottom: '24px', paddingBottom: '16px', borderBottom: '2px solid #e8e8e8', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '24px', fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Evaluation Results</h2>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              {currentEvaluation.status === 'pending' && (
                <><Spinner size={16} /><span style={{ fontSize: '14px', color: '#1890ff', fontWeight: 600 }}>Pending...</span></>
              )}
              {currentEvaluation.status === 'running' && (
                <><Spinner size={16} /><span style={{ fontSize: '14px', color: '#1890ff', fontWeight: 600 }}>Running...</span></>
              )}
              {currentEvaluation.status === 'completed' && (
                <span style={{ padding: '6px 16px', background: '#f6ffed', color: '#52c41a', borderRadius: '12px', fontSize: '12px', fontWeight: 700 }}>COMPLETED</span>
              )}
              {currentEvaluation.status === 'failed' && (
                <span style={{ padding: '6px 16px', background: '#fff1f0', color: '#ff4d4f', borderRadius: '12px', fontSize: '12px', fontWeight: 700 }}>FAILED</span>
              )}
            </div>
          </div>

          {/* Summary Stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <div style={{ padding: '16px', background: '#f5f5f5', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: '#8c8c8c', fontWeight: 600, marginBottom: '8px' }}>PROJECT</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#1a1a1a' }}>{currentEvaluation.project_title}</div>
            </div>
            <div style={{ padding: '16px', background: '#f5f5f5', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: '#8c8c8c', fontWeight: 600, marginBottom: '8px' }}>MODEL</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#1a1a1a' }}>{currentEvaluation.llm_model}</div>
            </div>
            <div style={{ padding: '16px', background: '#f5f5f5', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: '#8c8c8c', fontWeight: 600, marginBottom: '8px' }}>TOTAL QUOTES</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#1a1a1a' }}>{currentEvaluation.total_tasks}</div>
            </div>
            <div style={{ padding: '16px', background: '#f5f5f5', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: '#8c8c8c', fontWeight: 600, marginBottom: '8px' }}>LABELED QUOTES</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#1a1a1a' }}>{currentEvaluation.labeled_tasks}</div>
            </div>
          </div>

          {/* Download PDF Report Button for Completed Evaluations */}
          {currentEvaluation.status === 'completed' && (
            <div style={{ 
              display: 'flex', 
              justifyContent: 'center', 
              marginTop: '32px',
              marginBottom: '24px',
              paddingTop: '24px',
              borderTop: '2px solid #e8e8e8'
            }}>
              <Button 
                onClick={() => {
                  window.location.href = `/api/evaluations/${currentEvaluation.id}/download_report/`;
                }}
                style={{ 
                  padding: '14px 36px', 
                  fontSize: '16px', 
                  fontWeight: 600,
                  background: 'linear-gradient(135deg, #1890ff 0%, #0066cc 100%)',
                  color: 'white',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  boxShadow: '0 4px 16px rgba(24, 144, 255, 0.35)',
                  transition: 'all 0.25s ease'
                }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                Download Detailed PDF Report
              </Button>
            </div>
          )}

          {/* Error Message */}
          {currentEvaluation.status === 'failed' && currentEvaluation.error_message && (
            <div style={{ padding: '16px', background: '#fff1f0', border: '1px solid #ffa39e', borderRadius: '8px', color: '#ff4d4f' }}>
              <div style={{ fontWeight: 600, marginBottom: '8px' }}>Error:</div>
              <div>{currentEvaluation.error_message}</div>
            </div>
          )}

          {/* Close Button */}
          <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
            <Button 
              onClick={() => setShowResults(false)}
              style={{ padding: '10px 24px', fontSize: '14px', fontWeight: 600 }}
            >
              Close Results
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

EvalPage.title = 'Evaluation';
EvalPage.path = '/evaluation';
EvalPage.exact = true;
