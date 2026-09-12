import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";

function SecurityTab() {
  const [security, setSecurity] = useState(null);
  const [canaryResult, setCanaryResult] = useState(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    apiGet("/api/security/status").then(setSecurity).catch(() => {});
  }, [canaryResult]);

  const testCanary = async () => {
    setTesting(true);
    try {
      const result = await apiPost("/api/security/canary");
      setCanaryResult(result);
    } catch {
      setCanaryResult({ result: "ERROR", detail: "Failed to reach backend" });
    }
    setTesting(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1rem' }}>
      <div className="glass" style={{ padding: '0.75rem' }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.5rem' }}>External Connections</div>
        <div style={{ fontSize: '1.8rem', fontWeight: 700, fontFamily: 'monospace', color: (security?.external_connections ?? 0) === 0 ? '#10b981' : '#ef4444' }}>
          {security?.external_connections ?? "—"}
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          {(security?.external_connections ?? 0) === 0 ? "No data leaves the premises" : "ALERT: External connections detected"}
        </div>
      </div>

      <div className="glass" style={{ padding: '0.75rem' }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.5rem' }}>Egress Guard</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Blocked attempts: {security?.egress_blocked ?? 0}</div>
        <button onClick={testCanary} disabled={testing} className="btn" style={{ width: '100%', padding: '0.5rem', fontSize: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
          {testing ? "Testing..." : "🐤 Test Canary"}
        </button>
        {canaryResult && (
          <div style={{ marginTop: '0.5rem', padding: '0.5rem', borderRadius: '0.25rem', fontSize: '0.7rem', fontFamily: 'monospace', background: canaryResult.result === "BLOCKED" ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', color: canaryResult.result === "BLOCKED" ? '#10b981' : '#ef4444' }}>
            {canaryResult.result}: {canaryResult.detail?.substring(0, 80)}
          </div>
        )}
      </div>

      <div className="glass" style={{ padding: '0.75rem' }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.5rem' }}>Audit Chain</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
          <span style={{ color: security?.audit?.chain_valid ? '#10b981' : '#ef4444' }}>{security?.audit?.chain_valid ? "✓" : "✗"}</span>
          <span style={{ color: 'var(--text-secondary)' }}>{security?.audit?.entries ?? 0} entries</span>
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontFamily: 'monospace', marginTop: '0.25rem' }}>
          {security?.audit?.last_hash}
        </div>
      </div>
    </div>
  );
}

function SourcesTab({ events }) {
  const sources = [];
  for (const e of events) {
    if (e.type === "step.completed" && e.payload.ok && e.payload.data?.chunks) {
      sources.push(...e.payload.data.chunks);
    }
    if (e.type === "step.completed" && e.payload.ok && e.payload.data?.citations) {
      sources.push(...e.payload.data.citations);
    }
  }

  return (
    <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.5rem' }}>Retrieved Sources</div>
      {sources.length === 0 ? (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textAlign: 'center', padding: '1rem 0' }}>Sources will appear here when the agent retrieves documents</div>
      ) : (
        sources.map((s, i) => (
          <div key={i} className="glass" style={{ padding: '0.75rem', fontSize: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
              <span style={{ color: 'var(--accent-color)', fontFamily: 'monospace' }}>[{s.id || `C${i + 1}`}]</span>
              {s.score && <span style={{ color: 'var(--text-secondary)' }}>score={s.score.toFixed(2)}</span>}
            </div>
            <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{s.document}{s.page && <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>, p. {s.page}</span>}</div>
            {s.section && <div style={{ color: 'var(--text-secondary)', marginTop: '0.125rem' }}>{s.section}</div>}
            {s.text && (
              <details style={{ marginTop: '0.5rem' }}>
                <summary style={{ color: 'var(--accent-color)', cursor: 'pointer', outline: 'none', userSelect: 'none' }}>Show content</summary>
                <div style={{ color: 'var(--text-secondary)', marginTop: '0.5rem', lineHeight: 1.4 }}>{s.text}</div>
              </details>
            )}
          </div>
        ))
      )}
    </div>
  );
}

export default function Inspector({ events }) {
  const [tab, setTab] = useState("sources");

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ display: 'flex', borderBottom: '1px solid var(--glass-border)', flexShrink: 0 }}>
        {["sources", "models", "security"].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{ flex: 1, padding: '0.75rem 0', fontSize: '0.75rem', fontWeight: 500, textTransform: 'capitalize', background: 'transparent', border: 'none', cursor: 'pointer', borderBottom: tab === t ? '2px solid var(--accent-color)' : '2px solid transparent', color: tab === t ? 'var(--text-primary)' : 'var(--text-secondary)' }}
          >
            {t}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {tab === "security" && <SecurityTab />}
        {tab === "sources" && <SourcesTab events={events} />}
        {tab === "models" && <div style={{ padding: '1rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Model registry data goes here.</div>}
      </div>
    </div>
  );
}
