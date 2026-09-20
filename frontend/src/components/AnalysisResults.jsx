export default function AnalysisResults({ analysis, validation }) {
  if (!analysis) return null;

  return (
    <div className="analysis-results animate-fade-in" style={{ marginTop: '2rem' }}>
      <h3 style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem', marginBottom: '1rem', color: 'var(--text-light)' }}>
        Agent Reasoning Results
      </h3>

      {/* Validation Banner */}
      {validation && (
        <div className={`validation-banner ${validation.passed ? 'passed' : 'failed'}`}>
          <div className="validation-title">
            {validation.passed ? '✅ Validation Passed' : '🔴 Validation Failed'}
          </div>
          <div className="validation-metrics">
            <span>Unsupported Claims: <strong>{validation.unsupported_count}</strong></span>
            <span style={{ margin: '0 1rem' }}>|</span>
            <span>Invalid Citations: <strong>{validation.invalid_citations}</strong></span>
            <span style={{ margin: '0 1rem' }}>|</span>
            <span>Missing Evidence: <strong>{validation.missing_evidence ? 'Yes' : 'No'}</strong></span>
          </div>
          {validation.failure_reason && (
            <div className="validation-reason" style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
              <strong>Reason:</strong> {validation.failure_reason}
            </div>
          )}
        </div>
      )}

      {/* Task Class & Recommendation */}
      <div className="analysis-header" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem', backgroundColor: 'var(--bg-secondary)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
        <div>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Task Class</span>
          <div style={{ color: 'var(--accent-blue)', fontWeight: 'bold' }}>{analysis.task_class || 'General'}</div>
        </div>
        {analysis.recommended_action && (
          <div style={{ textAlign: 'right' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Recommended Action</span>
            <div style={{ color: 'var(--text-light)', fontWeight: 'bold' }}>{analysis.recommended_action}</div>
          </div>
        )}
      </div>

      {/* Supported Findings */}
      {analysis.supported_findings?.length > 0 && (
        <div className="claims-section">
          <h4 style={{ color: 'var(--accent-green)', marginBottom: '0.75rem' }}>Supported Findings</h4>
          <div className="claims-list">
            {analysis.supported_findings.map((claim, idx) => (
              <div key={`finding-${idx}`} className="claim-card">
                <div className="claim-text">✅ {claim.claim}</div>
                {claim.sources?.length > 0 && (
                  <div className="claim-sources">
                    {claim.sources.map((src, sIdx) => (
                      <span key={`src-${sIdx}`} className="source-badge">
                        {src.document} (pg {src.page})
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Inferences */}
      {analysis.inferences?.length > 0 && (
        <div className="claims-section" style={{ marginTop: '1.5rem' }}>
          <h4 style={{ color: 'var(--accent-blue)', marginBottom: '0.75rem' }}>Inferences</h4>
          <div className="claims-list">
            {analysis.inferences.map((claim, idx) => (
              <div key={`inf-${idx}`} className="claim-card">
                <div className="claim-text">💡 {claim.claim}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Uncertainties */}
      {analysis.uncertainties?.length > 0 && (
        <div className="claims-section" style={{ marginTop: '1.5rem' }}>
          <h4 style={{ color: 'var(--accent-amber)', marginBottom: '0.75rem' }}>Uncertainties</h4>
          <div className="claims-list">
            {analysis.uncertainties.map((claim, idx) => (
              <div key={`unc-${idx}`} className="claim-card">
                <div className="claim-text">⚠️ {claim.claim}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
