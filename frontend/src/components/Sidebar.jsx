/**
 * PRAHARÍ — Sidebar Component
 * Left panel with workflow navigation
 */

const WORKFLOWS = [
  { id: 'inspection', icon: '🔍', label: 'Inspection Analysis', description: 'Analyze reports & generate approval notes' },
  { id: 'coding', icon: '💻', label: 'Coding Agent', description: 'Generate, test & self-correct code' },
  { id: 'search', icon: '📚', label: 'Document Search', description: 'Search internal SOPs & manuals' },
];

export default function Sidebar({ activeWorkflow, onSelectWorkflow }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-section">
        <div className="sidebar-section-title">Workflows</div>
        {WORKFLOWS.map((wf) => (
          <div
            key={wf.id}
            className={`sidebar-item ${activeWorkflow === wf.id ? 'active' : ''}`}
            onClick={() => onSelectWorkflow(wf.id)}
            id={`workflow-${wf.id}`}
          >
            <span className="icon">{wf.icon}</span>
            <div>
              <div>{wf.label}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-title">System</div>
        <div className="sidebar-item" onClick={() => onSelectWorkflow('security')} id="workflow-security">
          <span className="icon">🛡️</span>
          <span>Security Status</span>
        </div>
        <div className="sidebar-item" onClick={() => onSelectWorkflow('audit')} id="workflow-audit">
          <span className="icon">📋</span>
          <span>Audit Log</span>
        </div>
      </div>

      <div className="sidebar-section" style={{ marginTop: 'auto', padding: '0 1.25rem' }}>
        <div className="demo-banner" style={{ marginTop: '1rem' }}>
          v1.0.0 Prototype
        </div>
      </div>
    </aside>
  );
}
