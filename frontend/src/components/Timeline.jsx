import React from "react";

function StepIcon({ ok, running }) {
  if (running) {
    return (
      <div style={{ width: '20px', height: '20px', borderRadius: '50%', border: '2px solid var(--accent-color)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-color)', animation: 'pulse 2s infinite' }} />
      </div>
    );
  }
  if (ok === true) {
    return <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.2)', color: '#10b981', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem' }}>✓</div>;
  }
  if (ok === false) {
    return <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem' }}>✗</div>;
  }
  return <div style={{ width: '20px', height: '20px', borderRadius: '50%', border: '1px solid var(--glass-border)', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem' }}>·</div>;
}

export default function Timeline({ events, runId }) {
  if (!events || events.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1rem 0' }}>
      {events.map((event, idx) => {
        const p = event.payload;
        switch (event.type) {
          case "run.started":
            return (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.25rem 0.5rem' }}>
                <StepIcon running />
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Run started · profile={p.profile}</span>
              </div>
            );
          case "stage.started":
            return (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.25rem 0.5rem' }}>
                <StepIcon running />
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-color)', textTransform: 'uppercase' }}>{p.stage}</span>
              </div>
            );
          case "plan.created":
            return (
              <div key={idx} className="glass" style={{ marginLeft: '1.75rem', marginTop: '0.25rem', marginBottom: '0.5rem', padding: '0.75rem', fontSize: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--accent-color)', fontWeight: 600 }}>PLAN</span>
                  <span style={{ padding: '0.1rem 0.3rem', borderRadius: '0.25rem', fontSize: '0.65rem', fontFamily: 'monospace', background: 'rgba(16, 185, 129, 0.2)', color: '#10b981' }}>{p.source === "recipe" ? `RECIPE: ${p.recipe}` : "freehand"}</span>
                </div>
                {(p.steps || []).map(s => (
                  <div key={s.id} style={{ display: 'flex', gap: '0.5rem', padding: '0.25rem 0', color: 'var(--text-secondary)' }}>
                    <span style={{ width: '1rem', textAlign: 'right', flexShrink: 0 }}>{s.id}.</span>
                    <span style={{ fontFamily: 'monospace', width: '8rem', flexShrink: 0 }}>{s.tool}</span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.why}</span>
                  </div>
                ))}
              </div>
            );
          case "step.started":
            return (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.25rem 0.5rem' }}>
                <StepIcon running />
                <span style={{ fontSize: '0.85rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>step {p.id}</span>{" "}
                  <span style={{ fontFamily: 'monospace' }}>{p.tool}</span>
                </span>
              </div>
            );
          case "step.completed":
            return (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.25rem 0.5rem' }}>
                <StepIcon ok={p.ok} />
                <span style={{ fontSize: '0.85rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>step {p.id}</span>{" "}
                  <span style={{ color: 'var(--text-secondary)' }}>({p.duration_ms}ms)</span>{" "}
                  <span style={{ color: p.ok ? 'var(--text-primary)' : '#ef4444' }}>{p.summary || p.error}</span>
                </span>
              </div>
            );
          case "artifact.created":
            return (
              <div key={idx} className="glass-card" style={{ marginLeft: '1.75rem', marginTop: '0.25rem', marginBottom: '0.5rem', padding: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'var(--glass-bg)' }}>
                <div style={{ fontSize: '1.5rem' }}>📄</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, fontSize: '0.85rem', color: 'var(--text-primary)' }}>{p.kind?.toUpperCase()}: {p.filename || p.relative_path}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.125rem' }}>Ready for download</div>
                </div>
                <button 
                  className="btn btn-primary" 
                  style={{ padding: '0.35rem 0.85rem', fontSize: '0.75rem' }}
                  onClick={() => window.open(`http://127.0.0.1:8077/api/runs/${runId}/artifacts/${p.filename || p.relative_path}`, "_blank")}
                >
                  Download
                </button>
              </div>
            );
          case "run.completed":
            return (
              <div key={idx} className="glass" style={{ margin: '0.75rem 0.5rem', padding: '0.75rem', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', fontWeight: 500, color: '#10b981' }}>✓ COMPLETED</div>
                {p.answer && (
                    <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'var(--glass-bg)', borderRadius: '0.25rem', color: 'var(--text-primary)', fontSize: '0.85rem', border: '1px solid var(--glass-border)', whiteSpace: 'pre-wrap' }}>
                        {p.answer}
                    </div>
                )}
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{p.steps} steps · {p.tokens} tokens · {p.elapsed_s}s</div>
              </div>
            );
          case "run.failed":
            return (
              <div key={idx} className="glass" style={{ margin: '0.75rem 0.5rem', padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', fontWeight: 500, color: '#ef4444' }}>✗ FAILED</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{p.error}</div>
              </div>
            );
          default:
            return null;
        }
      })}
    </div>
  );
}
