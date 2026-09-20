/**
 * PRAHARÍ — Agent Timeline Component
 * Live-updating timeline showing agent state machine progress
 */

export default function AgentTimeline({ events }) {
  if (!events || events.length === 0) {
    return (
      <div className="glass-card" style={{ textAlign: 'center', padding: '2rem' }}>
        <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem', opacity: 0.5 }}>🤖</div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Agent timeline will appear here when you run a task
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="card-title">Agent Timeline</span>
        <span style={{
          fontSize: '0.7rem',
          color: 'var(--accent-green)',
          fontFamily: 'var(--font-mono)',
          fontWeight: 600,
        }}>
          {events.length} events
        </span>
      </div>

      <div className="timeline">
        {events.map((event, idx) => (
          <TimelineItem key={idx} event={event} index={idx} />
        ))}
      </div>
    </div>
  );
}

function TimelineItem({ event, index }) {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return '✓';
      case 'started': return '⟳';
      case 'failed': return '✗';
      case 'error': return '!';
      default: return '•';
    }
  };

  const getDotClass = (status) => {
    switch (status) {
      case 'completed': return 'completed';
      case 'started': return 'running';
      case 'failed':
      case 'error': return 'failed';
      default: return 'pending';
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    try {
      const d = new Date(timestamp);
      return d.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return '';
    }
  };

  return (
    <div
      className="timeline-item"
      style={{ animationDelay: `${index * 0.08}s` }}
    >
      <div className={`timeline-dot ${getDotClass(event.status)}`}>
        {event.status === 'started' ? (
          <span className="spinner" style={{ width: 12, height: 12, borderWidth: 2 }}></span>
        ) : (
          getStatusIcon(event.status)
        )}
      </div>
      <div className="timeline-content">
        <div className="timeline-message">{event.message}</div>
        <div className="timeline-timestamp">{formatTime(event.timestamp)}</div>

        {/* Show code data if present */}
        {event.data?.code && (
          <div className="code-block" style={{ marginTop: '0.5rem', fontSize: '0.72rem', maxHeight: '200px', overflow: 'auto' }}>
            {event.data.code}
          </div>
        )}
        {event.data?.corrected_code && (
          <div className="code-block" style={{ marginTop: '0.5rem', fontSize: '0.72rem', maxHeight: '200px', overflow: 'auto' }}>
            {event.data.corrected_code}
          </div>
        )}
        {event.data?.error && (
          <div className="code-block" style={{ marginTop: '0.5rem', fontSize: '0.72rem', color: 'var(--accent-red)', maxHeight: '150px', overflow: 'auto' }}>
            {event.data.error}
          </div>
        )}
        {event.data?.output && (
          <div className="code-block" style={{ marginTop: '0.5rem', fontSize: '0.72rem', color: 'var(--accent-green)', maxHeight: '150px', overflow: 'auto' }}>
            {event.data.output}
          </div>
        )}
        {event.data?.plan && (
          <div style={{ marginTop: '0.4rem' }}>
            {event.data.plan.map((step, i) => (
              <div key={i} style={{
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
                padding: '0.15rem 0',
                paddingLeft: '0.5rem',
                borderLeft: '2px solid var(--border-primary)',
                marginBottom: '2px',
              }}>
                {i + 1}. {step}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
