/**
 * PRAHARÍ — Header Component
 * Top navigation bar with branding, status badges, and demo label
 */

export default function Header({ securityStatus }) {
  return (
    <header className="app-header">
      <div className="header-brand">
        <div>
          <div className="header-logo">PRAHARÍ</div>
          <div className="header-subtitle">Sovereign Industrial AI Workbench</div>
        </div>
      </div>

      <div className="header-status">
        <div className="demo-banner">
          Demo Environment — Synthetic Data
        </div>

        <div className="status-badge local">
          <span className="status-dot"></span>
          Local Mode
        </div>

        <div className="status-badge disconnected">
          🔒 {securityStatus?.network_mode || 'LOCAL_ONLY'}
        </div>
      </div>
    </header>
  );
}
