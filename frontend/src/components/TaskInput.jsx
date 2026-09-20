/**
 * PRAHARÍ — Task Input Component
 * Handles file upload, task description input, and Run Agent button
 */

import { useRef } from 'react';

export default function TaskInput({
  activeWorkflow,
  taskText,
  onTaskTextChange,
  uploadedFile,
  onFileUpload,
  onRunAgent,
  isRunning,
}) {
  const fileInputRef = useRef(null);

  const getPlaceholder = () => {
    switch (activeWorkflow) {
      case 'coding':
        return 'Write a Python function to calculate corrosion rate from thickness loss and time, then test it.';
      case 'search':
        return 'Search for corrosion acceptance criteria in internal SOPs...';
      default:
        return 'Analyze this inspection report and prepare an approval note using relevant internal SOP guidance.';
    }
  };

  const getTitle = () => {
    switch (activeWorkflow) {
      case 'coding': return 'Coding Agent';
      case 'search': return 'Document Search';
      default: return 'Inspection Analysis';
    }
  };

  const getIcon = () => {
    switch (activeWorkflow) {
      case 'coding': return '💻';
      case 'search': return '📚';
      default: return '🔍';
    }
  };

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="card-title">{getIcon()} {getTitle()}</span>
      </div>

      {/* File Upload Area (only for inspection workflow) */}
      {activeWorkflow === 'inspection' && (
        <div
          className={`upload-area ${uploadedFile ? 'has-file' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          id="upload-area"
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => onFileUpload(e.target.files[0])}
            style={{ display: 'none' }}
            accept=".pdf,.txt,.doc,.docx"
            id="file-input"
          />
          <div className="upload-icon">
            {uploadedFile ? '✅' : '📁'}
          </div>
          <div className="upload-text">
            {uploadedFile
              ? 'Document uploaded'
              : 'Click to upload inspection report (PDF, TXT, DOCX)'}
          </div>
          {uploadedFile && (
            <div className="upload-filename">{uploadedFile.name}</div>
          )}
        </div>
      )}

      {/* Task Description */}
      <div className="task-input-area" style={{ marginTop: activeWorkflow === 'inspection' ? '0.75rem' : 0 }}>
        <textarea
          className="task-textarea"
          value={taskText}
          onChange={(e) => onTaskTextChange(e.target.value)}
          placeholder={getPlaceholder()}
          id="task-textarea"
        />
      </div>

      {/* Actions */}
      <div className="task-actions">
        <button
          className="btn btn-primary"
          onClick={onRunAgent}
          disabled={isRunning || !taskText.trim()}
          id="run-agent-btn"
        >
          {isRunning ? (
            <><span className="spinner"></span> Agent Running...</>
          ) : (
            <>▶ Run Agent</>
          )}
        </button>

        {activeWorkflow === 'inspection' && (
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => {
              onTaskTextChange(
                'Analyze this inspection report for equipment HX-4021 and prepare an approval note using relevant internal SOP guidance.'
              );
            }}
            id="use-demo-btn"
          >
            📝 Use Demo Task
          </button>
        )}

        {activeWorkflow === 'coding' && (
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => {
              onTaskTextChange(
                'Write a Python function to calculate corrosion rate from thickness loss and time, then test it.'
              );
            }}
            id="use-demo-coding-btn"
          >
            📝 Use Demo Task
          </button>
        )}
      </div>
    </div>
  );
}
