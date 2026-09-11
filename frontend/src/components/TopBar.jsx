import React, { useEffect, useState } from "react";
import { apiGet } from "../lib/api";

export default function TopBar() {
  const [security, setSecurity] = useState(null);
  const [ollamaUp, setOllamaUp] = useState(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const sec = await apiGet("/api/security/status");
        setSecurity(sec);
      } catch {
        setSecurity(null);
      }
      try {
        const health = await apiGet("/api/health");
        setOllamaUp(health.ollama?.reachable ?? false);
      } catch {
        setOllamaUp(false);
      }
    };
    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, []);

  const extCount = security?.external_connections ?? 0;
  const auditCount = security?.audit?.entries ?? 0;
  const chainValid = security?.audit?.chain_valid ?? true;
  const blocked = security?.egress_blocked ?? 0;

  return (
    <header className="glass-card flex items-center justify-between px-6 py-3 shrink-0 z-50 mb-4" style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981', animation: 'pulse 2s infinite' }} />
          <span style={{ fontWeight: 600, fontSize: '1.1rem', color: 'var(--text-primary)' }}>PRAHARI</span>
        </div>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
          Sovereign Workbench
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', fontSize: '0.8rem', fontFamily: 'monospace' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
          <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: extCount === 0 ? '#10b981' : '#ef4444' }} />
          <span style={{ color: extCount === 0 ? '#10b981' : '#ef4444', fontWeight: 600 }}>AIR-GAPPED</span>
        </div>
        <span style={{ color: 'var(--text-secondary)' }}>·</span>
        <span style={{ color: extCount === 0 ? 'var(--text-secondary)' : '#ef4444' }}>{extCount} EXTERNAL</span>
        {blocked > 0 && (
          <>
            <span style={{ color: 'var(--text-secondary)' }}>·</span>
            <span style={{ color: '#f59e0b' }}>{blocked} BLOCKED</span>
          </>
        )}
        <span style={{ color: 'var(--text-secondary)' }}>·</span>
        <span style={{ color: chainValid ? 'var(--text-secondary)' : '#ef4444' }}>
          audit {chainValid ? "✓" : "✗"} {auditCount}
        </span>
      </div>
    </header>
  );
}
