/**
 * PRAHARÍ — Right Panel Component
 * Displays model profile, sources/citations, artifact download, and security status
 */

const API_BASE = 'http://localhost:8000';

export default function RightPanel({
  profile,
  sources,
  artifact,
  securityStatus,
  onEgressTest,
  egressResult,
  isTestingEgress,
}) {
  return (
    <aside className="right-panel">
      {/* Model Profile */}
      <div className="info-block">
        <div className="info-block-title">Model / Capability</div>
        {profile ? (
          <>
            <div className="info-row">
              <span className="info-label">Profile</span>
              <span className="info-value blue">{profile.name}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Model</span>
              <span className="info-value">{profile.model}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Mode</span>
              <span className="info-value green">{profile.mode}</span>
            </div>
          </>
        ) : (
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Awaiting task...</p>
        )}
      </div>

      {/* Sources / Citations */}
      <div className="info-block">
        <div className="info-block-title">Sources</div>
        {sources && sources.length > 0 ? (
          sources.map((source, idx) => {
            const scoreVal = typeof source.score === 'number' && !isNaN(source.score)
              ? `${Math.round(source.score * 100)}%`
              : 'N/A';
            return (
              <div key={idx} className="source-card">
                <div className="source-name">📄 {source.document || 'Unknown'}</div>
                <div className="source-detail">
                  {source.section || 'N/A'} — Page {source.page || '?'}
                </div>
                <span className="source-score">
                  {scoreVal} match
                </span>
              </div>
            );
          })
        ) : (
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No sources retrieved yet</p>
        )}
      </div>

      {/* Artifact */}
      {artifact && (
        <div className="artifact-card animate-fade-in">
          <div className="artifact-icon">📄</div>
          <div className="artifact-name">{artifact}</div>
          <a
            href={`${API_BASE}/artifacts/${artifact}`}
            download
            className="btn btn-success btn-sm"
            style={{ marginTop: '0.6rem', textDecoration: 'none' }}
            id="download-artifact-btn"
          >
            ⬇ Download Artifact
          </a>
        </div>
      )}

      {/* Security Status */}
      <div className="info-block">
        <div className="info-block-title">Security Status</div>
        <div className="security-grid">
          <div className="security-metric">
            <div className="security-metric-value green">
              {securityStatus?.external_api_calls ?? 0}
            </div>
            <div className="security-metric-label">External Calls</div>
          </div>
          <div className="security-metric">
            <div className="security-metric-value green">LOCAL</div>
            <div className="security-metric-label">Data Location</div>
          </div>
          <div className="security-metric">
            <div className="security-metric-value amber">
              {securityStatus?.network_mode || 'LOCAL_ONLY'}
            </div>
            <div className="security-metric-label">Network</div>
          </div>
          <div className="security-metric">
            <div className="security-metric-value green">NONE</div>
            <div className="security-metric-label">Cloud Provider</div>
          </div>
        </div>

        <button
          className="btn btn-secondary btn-sm"
          style={{ marginTop: '0.75rem', width: '100%' }}
          onClick={onEgressTest}
          disabled={isTestingEgress}
          id="egress-test-btn"
        >
          {isTestingEgress ? (
            <><span className="spinner"></span> Testing Egress...</>
          ) : (
            '🔒 Test Egress'
          )}
        </button>

        {egressResult && (
          <div
            className="animate-fade-in"
            style={{
              marginTop: '0.5rem',
              padding: '0.5rem',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.72rem',
              background: egressResult.all_blocked
                ? 'var(--accent-green-glow)'
                : 'var(--accent-amber-glow)',
              color: egressResult.all_blocked
                ? 'var(--accent-green)'
                : 'var(--accent-amber)',
              border: `1px solid ${egressResult.all_blocked
                ? 'rgba(16,185,129,0.3)'
                : 'rgba(245,158,11,0.3)'}`,
            }}
          >
            {egressResult.summary}
          </div>
        )}
      </div>

      {/* Audit Count */}
      <div className="info-block">
        <div className="info-block-title">Audit Trail</div>
        <div className="info-row">
          <span className="info-label">Events Logged</span>
          <span className="info-value blue">{securityStatus?.audit_events ?? 0}</span>
        </div>
      </div>
    </aside>
  );
}
