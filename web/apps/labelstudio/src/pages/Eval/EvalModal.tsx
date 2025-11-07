import { useState } from "react";
import { Button } from "@humansignal/ui";
import { Modal } from "@humansignal/ui/lib/modal";
import { IconClose } from "@humansignal/icons";
import "./EvalModal.scss";

interface EvalModalProps {
  opened: boolean;
  onClose: () => void;
}

const LLM_MODELS = [
  { id: "gpt-4", name: "GPT-4", provider: "OpenAI" },
  { id: "gpt-3.5-turbo", name: "GPT-3.5 Turbo", provider: "OpenAI" },
  { id: "claude-3-opus", name: "Claude 3 Opus", provider: "Anthropic" },
  { id: "claude-3-sonnet", name: "Claude 3 Sonnet", provider: "Anthropic" },
  { id: "gemini-pro", name: "Gemini Pro", provider: "Google" },
  { id: "llama-2-70b", name: "Llama 2 70B", provider: "Meta" },
];

export const EvalModal: React.FC<EvalModalProps> = ({ opened, onClose }) => {
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [apiKey, setApiKey] = useState<string>("");
  const [systemPrompt, setSystemPrompt] = useState<string>("");
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setUploadedFiles(Array.from(e.target.files));
    }
  };

  const handleRemoveFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = () => {
    // Validate required fields
    if (!selectedModel || !apiKey.trim() || !systemPrompt.trim()) {
      alert("Please fill in all required fields");
      return;
    }

    // TODO: Implement backend integration
    console.log("Eval Configuration:", {
      model: selectedModel,
      apiKey,
      systemPrompt,
      files: uploadedFiles,
    });

    // Reset form and close modal
    setSelectedModel("");
    setApiKey("");
    setSystemPrompt("");
    setUploadedFiles([]);
    onClose();
  };

  const handleClose = () => {
    onClose();
  };

  const isFormValid = selectedModel && apiKey.trim() && systemPrompt.trim();

  if (!opened) return null;

  return (
    <Modal
      visible={opened}
      onHide={handleClose}
      title="Evaluation Configuration"
      closeOnClickOutside={false}
      style={{ maxWidth: 680, width: '100%' }}
    >
      <div className="eval-modal">
        <div className="eval-modal__header">
          <p className="eval-modal__description">
            Configure your LLM model evaluation settings. Fields marked with <span className="eval-modal__required-text">*</span> are required.
          </p>
        </div>

        <div className="eval-modal__content">
          {/* 1. Select LLM Model */}
          <div className="eval-modal__field">
            <div className="eval-modal__field-header">
              <div className="eval-modal__field-label">
                <span className="eval-modal__field-number">1</span>
                <span className="eval-modal__field-title">Select LLM Model</span>
              </div>
              <span className="eval-modal__required-badge">Required</span>
            </div>
            <select
              className="eval-modal__select"
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

          {/* 2. Enter API Key */}
          <div className="eval-modal__field">
            <div className="eval-modal__field-header">
              <div className="eval-modal__field-label">
                <span className="eval-modal__field-number">2</span>
                <span className="eval-modal__field-title">Enter API Key</span>
              </div>
              <span className="eval-modal__required-badge">Required</span>
            </div>
            <input
              type="password"
              className="eval-modal__input"
              placeholder="sk-..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              autoComplete="off"
            />
            <p className="eval-modal__hint">
              <svg className="eval-modal__hint-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              Your API key will be encrypted and stored securely
            </p>
          </div>

          {/* 3. Enter System Prompt */}
          <div className="eval-modal__field">
            <div className="eval-modal__field-header">
              <div className="eval-modal__field-label">
                <span className="eval-modal__field-number">3</span>
                <span className="eval-modal__field-title">Enter System Prompt</span>
              </div>
              <span className="eval-modal__required-badge">Required</span>
            </div>
            <textarea
              className="eval-modal__textarea"
              placeholder="You are a helpful assistant that evaluates..."
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={4}
            />
            <p className="eval-modal__hint">
              <svg className="eval-modal__hint-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              Define the system behavior and instructions for the LLM evaluation
            </p>
          </div>

          {/* 4. Upload Files */}
          <div className="eval-modal__field">
            <div className="eval-modal__field-header">
              <div className="eval-modal__field-label">
                <span className="eval-modal__field-number">4</span>
                <span className="eval-modal__field-title">Upload Files</span>
              </div>
              <span className="eval-modal__optional-badge">Optional</span>
            </div>
            
            <div className="eval-modal__upload-wrapper">
              <input
                type="file"
                id="file-upload"
                className="eval-modal__file-input"
                onChange={handleFileUpload}
                multiple
                accept=".csv,.json,.txt"
              />
              <label htmlFor="file-upload" className="eval-modal__upload-area">
                <svg className="eval-modal__upload-icon" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <div className="eval-modal__upload-text">
                  <span className="eval-modal__upload-primary">Click to upload</span>
                  <span className="eval-modal__upload-secondary">or drag and drop</span>
                </div>
                <p className="eval-modal__upload-formats">CSV, JSON, TXT files</p>
              </label>
            </div>

            {uploadedFiles.length > 0 && (
              <div className="eval-modal__files">
                <div className="eval-modal__files-header">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                  </svg>
                  <span>{uploadedFiles.length} file{uploadedFiles.length > 1 ? 's' : ''} selected</span>
                </div>
                <div className="eval-modal__files-list">
                  {uploadedFiles.map((file, index) => (
                    <div key={index} className="eval-modal__file">
                      <svg className="eval-modal__file-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                        <polyline points="13 2 13 9 20 9"/>
                      </svg>
                      <div className="eval-modal__file-details">
                        <span className="eval-modal__file-name">{file.name}</span>
                        <span className="eval-modal__file-size">
                          {(file.size / 1024).toFixed(2)} KB
                        </span>
                      </div>
                      <button
                        className="eval-modal__file-remove"
                        onClick={() => handleRemoveFile(index)}
                        type="button"
                        aria-label="Remove file"
                      >
                        <IconClose />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="eval-modal__footer">
          <Button look="outlined" onClick={handleClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!isFormValid}>
            Create Evaluation
          </Button>
        </div>
      </div>
    </Modal>
  );
};
