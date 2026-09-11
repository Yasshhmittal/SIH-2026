import React, { useState, useRef } from "react";

export default function PromptInput({ onSubmit, disabled, status }) {
  const [text, setText] = useState("");
  const textareaRef = useRef(null);

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

  return (
    <form onSubmit={handleSubmit} className="glass-card" style={{ padding: '1rem', marginTop: '1rem' }}>
      {status && status !== "idle" && status !== "completed" && (
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {status === "running" && (
            <>
              <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--accent-color)', animation: 'pulse 2s infinite' }} />
              Agent is working...
            </>
          )}
          {status === "connecting" && "Connecting..."}
          {status === "failed" && <span style={{ color: '#ef4444' }}>Run failed</span>}
        </div>
      )}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem' }}>
        <button
          type="button"
          disabled={disabled}
          style={{ flexShrink: 0, width: '32px', height: '32px', borderRadius: '0.375rem', background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
          title="Attach file"
        >
          📎
        </button>
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            handleInput();
          }}
          onKeyDown={handleKeyDown}
          placeholder="Draft an approval note for the thickness deficiency at Elbow E-14..."
          disabled={disabled}
          rows={1}
          style={{ flex: 1, resize: 'none', background: 'var(--glass-bg)', color: 'var(--text-primary)', fontSize: '0.9rem', borderRadius: '0.5rem', padding: '0.5rem 0.75rem', border: '1px solid var(--glass-border)', outline: 'none', maxHeight: '160px', fontFamily: 'inherit' }}
        />
        <button
          type="submit"
          disabled={disabled || !text.trim()}
          className="btn btn-primary"
          style={{ flexShrink: 0, width: '32px', height: '32px', padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
          ↑
        </button>
      </div>
    </form>
  );
}
