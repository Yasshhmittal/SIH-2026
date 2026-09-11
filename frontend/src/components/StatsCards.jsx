import React from 'react';
import { Download, Users, Lock, Server, ArrowUpRight } from 'lucide-react';

const StatsCards = () => {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '1.5rem',
      padding: '2rem 0 4rem 0',
      width: '100%',
      zIndex: 2
    }}>
      {/* Left Column - Stats */}
      <div className="glass-card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <span style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#ef4444' }}></span>
            <span style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#f59e0b' }}></span>
            <span style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#10b981' }}></span>
          </div>
          <div style={{ height: '24px', flex: 1, backgroundColor: 'rgba(0,0,0,0.03)', borderRadius: '4px', display: 'flex', alignItems: 'center', padding: '0 0.5rem', fontSize: '0.75rem', color: '#9ca3af' }}>
            <Lock size={12} style={{ marginRight: '4px' }} /> localhost:8000
          </div>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
          <StatBox icon={<Lock size={18} color="#10b981"/>} value="100%" label="Air-Gapped" />
          <StatBox icon={<Download size={18} color="#3b82f6"/>} value="0" label="External Calls" />
          <StatBox icon={<Server size={18} color="#8b5cf6"/>} value="6GB" label="Min VRAM" />
        </div>

        <div style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.02)', borderRadius: '12px', padding: '1.5rem', marginTop: '1rem' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between' }}>
            SYSTEM LOGS <ArrowUpRight size={14} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontFamily: 'monospace', fontSize: '0.8rem', color: '#6b7280' }}>
            <div style={{ display: 'flex', gap: '1rem' }}><span style={{ color: '#10b981' }}>[OK]</span> <span>Qwen2.5:3b loaded in 1.2s</span></div>
            <div style={{ display: 'flex', gap: '1rem' }}><span style={{ color: '#10b981' }}>[OK]</span> <span>Qdrant index synchronized</span></div>
            <div style={{ display: 'flex', gap: '1rem' }}><span style={{ color: '#3b82f6' }}>[SEC]</span> <span>In-process egress guard active</span></div>
          </div>
        </div>
      </div>

      {/* Right Column - Chat Preview */}
      <div className="glass-card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
          <div style={{ width: 24, height: 24, borderRadius: '6px', background: '#0b0c10', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <span style={{ color: 'white', fontSize: '10px' }}>AI</span>
          </div>
          <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>PRAHARI Agent</span>
        </div>

        <div style={{ fontSize: '0.9rem', marginBottom: '1.5rem', fontWeight: 500 }}>
          Draft approval note per SOP for the attached inspection report.
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem' }}>
          <TimelineItem icon="✓" text="Parsed PDF and detected table via VL-3B" />
          <TimelineItem icon="✓" text="Retrieved SOP-INS-07 §4.2 (Retirement thickness)" />
          <TimelineItem icon="✓" text="Calculated corrosion rate: 0.42 mm/yr" />
          
          <div style={{ marginTop: '0.5rem', padding: '1rem', backgroundColor: '#fff', borderRadius: '8px', border: '1px solid #f3f4f6', boxShadow: '0 2px 10px rgba(0,0,0,0.02)' }}>
            <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Approval_Note_Draft_v1.docx</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '1rem' }}>Based on findings, minimum thickness (6.4mm) is violated...</div>
            <button className="btn" style={{ padding: '0.4rem 1rem', fontSize: '0.8rem', background: '#f3f4f6', color: '#374151' }}>Preview Document</button>
          </div>
        </div>
      </div>
    </div>
  );
};

const StatBox = ({ icon, value, label }) => (
  <div style={{
    backgroundColor: '#fff',
    border: '1px solid #f3f4f6',
    borderRadius: '12px',
    padding: '1.25rem 1rem',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '0.5rem',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.02)'
  }}>
    <div style={{ width: 32, height: 32, borderRadius: '8px', backgroundColor: '#f9fafb', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      {icon}
    </div>
    <div style={{ fontSize: '1.5rem', fontWeight: 700, lineHeight: 1 }}>{value}</div>
    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</div>
  </div>
);

const TimelineItem = ({ icon, text }) => (
  <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
    <div style={{ color: '#10b981', fontSize: '0.8rem', marginTop: '2px', fontWeight: 700 }}>{icon}</div>
    <div style={{ color: '#4b5563' }}>{text}</div>
  </div>
);

export default StatsCards;
