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
    <div className="eval-page">
      <div className="eval-page__header">
        <h1 className="eval-page__title">LLM Model Evaluation</h1>
        <p className="eval-page__subtitle">
          Configure and run evaluations on your language models. Test different models, prompts, and datasets to compare performance.
        </p>
      </div>

      <div className="eval-page__form-container">
        <div className="eval-page__form">
          {/* Field 1: Select LLM Model */}
          <div className="eval-page__field">
            <label className="eval-page__label">
              <span className="eval-page__label-number">1</span>
              <span className="eval-page__label-text">Select LLM Model</span>
              <span className="eval-page__label-required">*</span>
            </label>
            <select
              className="eval-page__input eval-page__select"
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
          <div className="eval-page__field">
            <label className="eval-page__label">
              <span className="eval-page__label-number">2</span>
              <span className="eval-page__label-text">Enter API Key</span>
              <span className="eval-page__label-required">*</span>
            </label>
            <input
              type="password"
              className="eval-page__input"
              placeholder="sk-..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              autoComplete="off"
            />
            <div className="eval-page__help-text">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              <span>Your API key will be encrypted and stored securely</span>
            </div>
          </div>

          {/* Field 3: Enter System Prompt */}
          <div className="eval-page__field">
            <label className="eval-page__label">
              <span className="eval-page__label-number">3</span>
              <span className="eval-page__label-text">Enter System Prompt</span>
              <span className="eval-page__label-required">*</span>
            </label>
            <textarea
              className="eval-page__input eval-page__textarea"
              placeholder="You are a helpful assistant that evaluates..."
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={4}
            />
            <div className="eval-page__help-text">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <span>Define the system behavior and instructions for the LLM evaluation</span>
            </div>
          </div>

          {/* Field 4: Upload Files */}
          <div className="eval-page__field">
            <label className="eval-page__label">
              <span className="eval-page__label-number">4</span>
              <span className="eval-page__label-text">Upload Files</span>
              <span className="eval-page__label-optional">Optional</span>
            </label>
            
            <div className="eval-page__upload-container">
              <input
                type="file"
                id="file-upload-eval"
                className="eval-page__file-input"
                onChange={handleFileUpload}
                multiple
                accept=".csv,.json,.txt"
              />
              <label htmlFor="file-upload-eval" className="eval-page__upload-zone">
                <svg className="eval-page__upload-icon" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <div>
                  <div className="eval-page__upload-title">Click to upload or drag and drop</div>
                  <div className="eval-page__upload-subtitle">CSV, JSON, TXT files</div>
                </div>
              </label>
            </div>

            {uploadedFiles.length > 0 && (
              <div className="eval-page__files-list">
                {uploadedFiles.map((file, index) => (
                  <div key={index} className="eval-page__file-item">
                    <svg className="eval-page__file-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                      <polyline points="13 2 13 9 20 9"/>
                    </svg>
                    <div className="eval-page__file-info">
                      <span className="eval-page__file-name">{file.name}</span>
                      <span className="eval-page__file-size">{(file.size / 1024).toFixed(2)} KB</span>
                    </div>
                    <button
                      className="eval-page__file-delete"
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
          <div className="eval-page__actions">
            <Button onClick={handleSubmit} disabled={!isFormValid}>
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
