import React, { useState, useRef } from "react";
import { uploadDocument } from "../lib/api";

const ACCEPT = ".pdf,.docx,.xlsx,.xlsm,.pptx,.txt,.md,.csv,.log,.png,.jpg,.jpeg,.webp,.bmp,.tiff";

export default function PromptInput({ onSubmit, disabled, status, orgId = "mrpl", onUploaded }) {
  const [text, setText] = useState("");
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleSubmit = (e) => {
    e?.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  };

  const handleFiles = async (files) => {
    if (!files?.length) return;
    setUploading(true);
    setNotice(null);

    const done = [];
    const failed = [];

    for (const file of Array.from(files)) {
      try {
        const result = await uploadDocument(file, orgId);
        const ingest = result.ingest;
        if (ingest.ok) {
          done.push(`${ingest.filename} — ${ingest.chunks} chunks indexed`);
          // Warnings are the honest part: a scanned PDF indexes with no text,
          // and the user needs to know that before asking about it.
          ingest.warnings?.forEach((w) => failed.push(`${ingest.filename}: ${w}`));
        } else {
          failed.push(`${ingest.filename}: ${ingest.error}`);
        }
      } catch (err) {
        failed.push(`${file.name}: ${err.message}`);
      }
    }

    setUploading(false);
    setNotice({ done, failed });
    if (done.length) onUploaded?.();
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (!disabled && !uploading) handleFiles(e.dataTransfer.files);
  };

  const busy = disabled || uploading;

  return (
    <form
      onSubmit={handleSubmit}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      className="glass-card"
      style={{ padding: "1rem", marginTop: "1rem" }}
    >
      {status && status !== "idle" && status !== "completed" && (
        <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          {status === "running" && (
            <>
              <div style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "var(--accent-color)", animation: "pulse 2s infinite" }} />
              Agent is working...
            </>
          )}
          {status === "connecting" && "Connecting..."}
          {status === "failed" && <span style={{ color: "#ef4444" }}>Run failed</span>}
        </div>
      )}

      {uploading && (
        <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginBottom: "0.5rem" }}>
          Indexing document...
        </div>
      )}

      {notice && (
        <div style={{ fontSize: "0.7rem", marginBottom: "0.5rem", display: "flex", flexDirection: "column", gap: "0.2rem" }}>
          {notice.done.map((line) => (
            <span key={line} style={{ color: "#22c55e" }}>✓ {line}</span>
          ))}
          {notice.failed.map((line) => (
            <span key={line} style={{ color: "#f59e0b" }}>! {line}</span>
          ))}
          <button
            type="button"
            onClick={() => setNotice(null)}
            style={{ alignSelf: "flex-start", background: "none", border: "none", color: "var(--text-secondary)", cursor: "pointer", fontSize: "0.65rem", padding: 0, marginTop: "0.2rem" }}
          >
            dismiss
          </button>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPT}
        multiple
        onChange={(e) => handleFiles(e.target.files)}
        style={{ display: "none" }}
      />

      {/* File Upload Area */}
      <div
        className={`upload-area ${(notice && notice.done.length > 0) ? 'has-file' : ''}`}
        onClick={() => fileInputRef.current?.click()}
        style={{ opacity: busy ? 0.5 : 1, pointerEvents: busy ? "none" : "auto" }}
      >
        <div className="upload-icon">
          {(notice && notice.done.length > 0) ? '✅' : '📁'}
        </div>
        <div className="upload-text">
          {(notice && notice.done.length > 0)
            ? 'Document uploaded successfully'
            : 'Click to attach a document (PDF, Word, Excel, PPT, TXT) — or drop it here'}
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "flex-end", gap: "0.75rem" }}>
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            handleInput();
          }}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your documents, or draft a deliverable..."
          disabled={disabled}
          rows={1}
          style={{ flex: 1, resize: "none", background: "var(--glass-bg)", color: "var(--text-primary)", fontSize: "0.95rem", borderRadius: "0.5rem", padding: "0.6rem 1rem", minHeight: "44px", border: "1px solid var(--glass-border)", outline: "none", maxHeight: "160px", fontFamily: "inherit", transition: "border-color 0.2s" }}
          onFocus={(e) => e.target.style.borderColor = "var(--accent-color)"}
          onBlur={(e) => e.target.style.borderColor = "var(--glass-border)"}
        />
        <button
          type="submit"
          disabled={disabled || !text.trim()}
          className="btn btn-primary"
          style={{ flexShrink: 0, width: "44px", height: "44px", padding: 0, borderRadius: "0.5rem", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1.2rem" }}
        >
          ↑
        </button>
      </div>
    </form>
  );
}
