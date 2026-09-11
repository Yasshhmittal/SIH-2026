import React, { useState } from "react";

export default function Sidebar({ onNewThread }) {
  const [org, setOrg] = useState("mrpl");
  const [threads] = useState([]);

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '1rem', borderBottom: '1px solid var(--glass-border)' }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.5rem' }}>
          Organisation
        </div>
        <select
          value={org}
          onChange={(e) => setOrg(e.target.value)}
          style={{ width: '100%', background: 'var(--glass-bg)', color: 'var(--text-primary)', fontSize: '0.85rem', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid var(--glass-border)', outline: 'none' }}
        >
          <option value="mrpl">MRPL</option>
          <option value="defence_unit_a">Defence Unit A</option>
        </select>
      </div>

      <div style={{ padding: '1rem' }}>
        <button
          onClick={onNewThread}
          className="btn btn-primary"
          style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', padding: '0.5rem' }}
        >
          + New Task
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 0.5rem' }}>
        {threads.length === 0 ? (
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem 1rem' }}>
            Start a new task to begin.
            <div style={{ fontSize: '0.65rem', marginTop: '0.5rem' }}>
              AI comes to your data — not the other way around.
            </div>
          </div>
        ) : null}
      </div>

      <div style={{ padding: '1rem', borderTop: '1px solid var(--glass-border)', textAlign: 'center' }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          PRAHARI v0.1.0 · On-Premise
        </div>
      </div>
    </div>
  );
}
