import React from 'react';
import { FileText, CornerRightDown } from 'lucide-react';

const Hero = () => {
  return (
    <section style={{
      textAlign: 'center',
      maxWidth: '800px',
      margin: '0 auto',
      zIndex: 2,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center'
    }}>
      {/* Small top badge */}
      <div style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.25rem 0.75rem',
        borderRadius: '9999px',
        border: '1px solid #e5e7eb',
        fontSize: '0.8rem',
        fontWeight: 500,
        marginBottom: '2rem',
        backgroundColor: 'rgba(255,255,255,0.5)'
      }}>
        <span style={{ color: '#10b981', display: 'flex' }}><ShieldIcon /></span> Sovereign AI Workbench
      </div>

      <h1 style={{
        color: '#1e1f24',
        textShadow: '0px 1px 0px #3a3b42, 0px 2px 0px #4a4b53, 0px 3px 0px #5a5b63, 0px 4px 0px #6a6b73, 0px 5px 0px #7a7b83, 0px 6px 10px rgba(0, 0, 0, 0.15), 0px 10px 20px rgba(0, 0, 0, 0.08)',
        letterSpacing: '-0.02em'
      }}>
        AI comes to your data<br />
        <span style={{ color: '#6e7179', textShadow: '0px 1px 0px #7e7f87, 0px 2px 0px #8e8f97, 0px 3px 0px #9ea0a7, 0px 4px 6px rgba(0, 0, 0, 0.1)' }}>not the other way around.</span>
      </h1>

      <p style={{ maxWidth: '600px', margin: '0 auto 2.5rem auto' }}>
        Sovereign On-Premise Agentic AI Workbench using Open-Weight Multimodal LLMs for Confidential Industrial Work.
      </p>

      {/* Action Input Area */}
      <div className="glass" style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        padding: '0.75rem 1rem',
        borderRadius: '12px',
        fontSize: '0.95rem',
        color: 'var(--text-secondary)',
        cursor: 'pointer'
      }}>
        <span>Upload</span>
        <div style={{
          padding: '0.25rem 0.5rem',
          background: 'rgba(0,0,0,0.05)',
          borderRadius: '4px',
          fontWeight: 600,
          color: 'var(--text-primary)'
        }}>Document</div>
        <span>to start an agentic task</span>
        <FileText size={18} color="#3b82f6" />
      </div>
      
      {/* Curved text hint */}
      <div style={{ marginTop: '3rem', position: 'relative' }}>
        <svg width="400" height="100" viewBox="0 0 400 100">
          <defs>
            <filter id="curveText3D" x="-10%" y="-10%" width="120%" height="140%">
              <feDropShadow dx="0" dy="1" stdDeviation="0" floodColor="#555" floodOpacity="0.6" />
              <feDropShadow dx="0" dy="2" stdDeviation="0" floodColor="#777" floodOpacity="0.4" />
              <feDropShadow dx="0" dy="3" stdDeviation="1" floodColor="#999" floodOpacity="0.3" />
              <feDropShadow dx="0" dy="5" stdDeviation="3" floodColor="#000" floodOpacity="0.1" />
            </filter>
          </defs>
          <path id="curve" d="M 50 80 Q 200 -20 350 80" fill="transparent" />
          <text width="400" style={{ fontSize: '14px', fill: '#6b7280', letterSpacing: '2px', fontWeight: 600 }} filter="url(#curveText3D)">
            <textPath href="#curve" startOffset="50%" textAnchor="middle">
              prahari securely indexes your entire knowledge base
            </textPath>
          </text>
        </svg>
        <div style={{ position: 'absolute', right: '40px', bottom: '40px' }}>
          <CornerRightDown size={20} color="#d1d5db" />
        </div>
      </div>
    </section>
  );
};

// Simple inline icon component
const ShieldIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  </svg>
);

export default Hero;
