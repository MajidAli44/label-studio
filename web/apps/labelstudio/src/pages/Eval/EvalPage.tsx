import React, { useState } from 'react';
import { Button } from '@humansignal/ui';
import { useUpdatePageTitle } from '@humansignal/core';
import { IconClose } from '@humansignal/icons';
import './EvalPage.scss';
import type { Page } from '../types/Page';

const LLM_MODELS = [
  { id: "gpt-4", name: "GPT-4", provider: "OpenAI" },
  { id: "gpt-3.5-turbo", name: "GPT-3.5 Turbo", provider: "OpenAI" },
  { id: "claude-3-opus", name: "Claude 3 Opus", provider: "Anthropic" },
  { id: "claude-3-sonnet", name: "Claude 3 Sonnet", provider: "Anthropic" },
  { id: "gemini-pro", name: "Gemini Pro", provider: "Google" },
  { id: "llama-2-70b", name: "Llama 2 70B", provider: "Meta" },
];

export const EvalPage: Page = () => {
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [apiKey, setApiKey] = useState<string>("");
  const [systemPrompt, setSystemPrompt] = useState<string>("");
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  useUpdatePageTitle('Eval');

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setUploadedFiles(Array.from(e.target.files));
    }
  };

  const handleRemoveFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = () => {
    if (!selectedModel || !apiKey.trim() || !systemPrompt.trim()) {
      alert("Please fill in all required fields");
      return;
    }

    console.log("Eval Configuration:", {
      model: selectedModel,
      apiKey,
      systemPrompt,
      files: uploadedFiles,
    });

    // Reset form after submission
    setSelectedModel("");
    setApiKey("");
    setSystemPrompt("");
    setUploadedFiles([]);
    
    alert("Evaluation created successfully!");
  };

  const isFormValid = selectedModel && apiKey.trim() && systemPrompt.trim();

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
              <span className="eval-page__label-text" style={{ flex: 1, fontSize: '16px' }}>Enter API Key</span>
              <span className="eval-page__label-required" style={{ color: '#ff4d4f', fontSize: '20px', fontWeight: 700, marginLeft: '4px' }}>*</span>
            </label>
            <input
              type="password"
              className="eval-page__input"
              style={{
                width: '100%',
                padding: '14px 18px',
                border: '2px solid #d9d9d9',
                borderRadius: '8px',
                fontSize: '15px',
                fontFamily: 'inherit',
                color: '#262626',
                background: '#ffffff',
                transition: 'all 0.25s ease',
                boxSizing: 'border-box'
              }}
              placeholder="sk-..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              autoComplete="off"
            />
            <div className="eval-page__help-text" style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', marginTop: '10px', padding: '12px 14px', background: '#f7f7f7', borderRadius: '6px', fontSize: '13px', color: '#595959', lineHeight: 1.6 }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, color: '#8c8c8c', marginTop: '2px' }}>
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              <span>Your API key will be encrypted and stored securely</span>
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

          {/* Field 4: Upload Files */}
          <div className="eval-page__field" style={{ marginBottom: '36px' }}>
            <label className="eval-page__label" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px', fontSize: '16px', fontWeight: 600, color: '#1a1a1a' }}>
              <span className="eval-page__label-number" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '32px', height: '32px', background: 'linear-gradient(135deg, #1890ff 0%, #0066cc 100%)', color: 'white', borderRadius: '50%', fontSize: '14px', fontWeight: 700, flexShrink: 0, boxShadow: '0 3px 8px rgba(24, 144, 255, 0.35)' }}>4</span>
              <span className="eval-page__label-text" style={{ flex: 1, fontSize: '16px' }}>Upload Files</span>
              <span className="eval-page__label-optional" style={{ padding: '4px 14px', background: 'linear-gradient(135deg, #f6ffed 0%, #e8f8e0 100%)', color: '#52c41a', border: '1px solid #b7eb8f', borderRadius: '14px', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.6px', boxShadow: '0 1px 3px rgba(82, 196, 26, 0.1)' }}>Optional</span>
            </label>
            
            <div className="eval-page__upload-container" style={{ marginTop: '10px' }}>
              <input
                type="file"
                id="file-upload-eval"
                className="eval-page__file-input"
                style={{ position: 'absolute', width: '1px', height: '1px', opacity: 0, pointerEvents: 'none' }}
                onChange={handleFileUpload}
                multiple
                accept=".csv,.json,.txt"
              />
              <label htmlFor="file-upload-eval" className="eval-page__upload-zone" style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                justifyContent: 'center', 
                padding: '44px 28px', 
                border: '2px dashed #d0d0d0', 
                borderRadius: '10px', 
                background: 'linear-gradient(135deg, #fafafa 0%, #f3f3f3 100%)', 
                cursor: 'pointer', 
                transition: 'all 0.3s ease' 
              }}>
                <svg className="eval-page__upload-icon" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: '#1890ff', marginBottom: '18px', transition: 'all 0.3s ease' }}>
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <div>
                  <div className="eval-page__upload-title" style={{ fontSize: '16px', fontWeight: 600, color: '#262626', marginBottom: '8px' }}>Click to upload or drag and drop</div>
                  <div className="eval-page__upload-subtitle" style={{ fontSize: '14px', color: '#8c8c8c', fontWeight: 500 }}>CSV, JSON, TXT files</div>
                </div>
              </label>
            </div>

            {uploadedFiles.length > 0 && (
              <div className="eval-page__files-list" style={{ marginTop: '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {uploadedFiles.map((file, index) => (
                  <div key={index} className="eval-page__file-item" style={{ display: 'flex', alignItems: 'center', gap: '14px', padding: '14px 18px', background: '#fafafa', border: '1px solid #e8e8e8', borderRadius: '8px', transition: 'all 0.2s ease' }}>
                    <svg className="eval-page__file-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, color: '#1890ff' }}>
                      <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                      <polyline points="13 2 13 9 20 9"/>
                    </svg>
                    <div className="eval-page__file-info" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <span className="eval-page__file-name" style={{ fontSize: '14px', fontWeight: 600, color: '#262626', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</span>
                      <span className="eval-page__file-size" style={{ fontSize: '12px', color: '#8c8c8c', fontWeight: 500 }}>{(file.size / 1024).toFixed(2)} KB</span>
                    </div>
                    <button
                      className="eval-page__file-delete"
                      style={{ flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', width: '34px', height: '34px', padding: 0, background: 'transparent', border: '1px solid #d9d9d9', borderRadius: '7px', color: '#8c8c8c', cursor: 'pointer', transition: 'all 0.25s ease' }}
                      onClick={() => handleRemoveFile(index)}
                      type="button"
                      aria-label="Remove file"
                    >
                      <IconClose />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Submit Button */}
          <div className="eval-page__actions" style={{ marginTop: '48px', paddingTop: '36px', borderTop: '2px solid #e8e8e8', display: 'flex', justifyContent: 'center' }}>
            <Button 
              onClick={handleSubmit} 
              disabled={!isFormValid}
              style={{ 
                minWidth: '220px', 
                padding: '14px 40px', 
                fontSize: '16px', 
                fontWeight: 600, 
                borderRadius: '8px', 
                transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)', 
                boxShadow: !isFormValid ? 'none' : '0 2px 8px rgba(24, 144, 255, 0.2)'
              }}
            >
              Create Evaluation
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

EvalPage.title = 'Eval';
EvalPage.path = '/eval';
EvalPage.exact = true;
