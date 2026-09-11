import React from 'react';
import { Database, FileCode, FileText, Bot, ShieldCheck, HardDrive } from 'lucide-react';

const VisualHub = () => {
  return (
    <div style={{
      position: 'relative',
      width: '100%',
      height: '350px',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      marginTop: '-2rem',
      zIndex: 1
    }}>
      {/* Connecting lines */}
      <svg style={{ position: 'absolute', width: '100%', height: '100%', zIndex: 0 }} overflow="visible">
        <path d="M 50% 50% Q 25% 20% 20% 10%" fill="none" stroke="#e5e7eb" strokeWidth="2" strokeDasharray="5,5" />
        <path d="M 50% 50% Q 75% 20% 80% 10%" fill="none" stroke="#e5e7eb" strokeWidth="2" strokeDasharray="5,5" />
        <path d="M 50% 50% Q 25% 80% 20% 90%" fill="none" stroke="#e5e7eb" strokeWidth="2" strokeDasharray="5,5" />
        <path d="M 50% 50% Q 75% 80% 80% 90%" fill="none" stroke="#e5e7eb" strokeWidth="2" strokeDasharray="5,5" />
      </svg>

      {/* Center Node */}
      <div className="glass-card" style={{
        width: '260px',
        height: '150px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        borderRadius: '50% 50% 50% 50% / 60% 60% 40% 40%',
        boxShadow: `
          0 4px 0px #c8c9cd,
          0 8px 0px #b0b1b6,
          0 12px 0px #98999e,
          0 16px 30px rgba(0, 0, 0, 0.12),
          0 24px 50px rgba(0, 0, 0, 0.06),
          inset 0 -4px 12px rgba(0, 0, 0, 0.04),
          inset 0 2px 8px rgba(255, 255, 255, 0.9)
        `,
        zIndex: 2,
        position: 'relative',
        background: 'linear-gradient(145deg, rgba(255,255,255,0.95) 0%, rgba(245,245,248,0.9) 40%, rgba(235,236,240,0.85) 100%)',
        border: '1px solid rgba(255,255,255,0.6)',
        transform: 'perspective(600px) rotateX(5deg)',
        transition: 'transform 0.3s ease, box-shadow 0.3s ease'
      }}>
        <div style={{
          position: 'absolute', width: '100%', height: '100%', 
          borderRadius: 'inherit',
          boxShadow: '0 0 60px rgba(0, 0, 0, 0.06), 0 0 100px rgba(0, 0, 0, 0.03)',
          zIndex: -1
        }}></div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.35rem', fontWeight: 700 }}>
          <span style={{ color: '#8b5cf6', textShadow: '0 1px 0 #7c3aed, 0 2px 0 #6d28d9' }}>│││</span>
          <span style={{ 
            color: '#1e1f24', 
            textShadow: '0px 1px 0px #3a3b42, 0px 2px 0px #5a5b63, 0px 3px 6px rgba(0, 0, 0, 0.15)',
            letterSpacing: '0.05em'
          }}>PRAHARI</span>
          <span style={{ color: '#8b5cf6', textShadow: '0 1px 0 #7c3aed, 0 2px 0 #6d28d9' }}>│││</span>
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem', fontWeight: 500 }}>
          Local AI Core
        </div>
      </div>

      {/* Orbit Nodes */}
      <OrbitNode icon={<FileText size={24} color="#ef4444" />} top="10%" left="20%" label="PDF Scans" />
      <OrbitNode icon={<FileCode size={24} color="#3b82f6" />} top="10%" right="20%" label="Sandbox" />
      <OrbitNode icon={<Database size={24} color="#10b981" />} bottom="10%" left="20%" label="Qdrant DB" />
      <OrbitNode icon={<Bot size={24} color="#f59e0b" />} bottom="10%" right="20%" label="Qwen 2.5" />
      <OrbitNode icon={<ShieldCheck size={24} color="#8b5cf6" />} top="45%" left="8%" label="Air-Gapped" />
      <OrbitNode icon={<HardDrive size={24} color="#64748b" />} top="45%" right="8%" label="SOPs" />
    </div>
  );
};

const OrbitNode = ({ icon, top, bottom, left, right, label }) => (
  <div style={{
    position: 'absolute',
    top, bottom, left, right,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '0.5rem',
    zIndex: 2
  }}>
    <div className="glass" style={{
      width: '56px', height: '56px',
      borderRadius: '50%',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      background: 'rgba(255,255,255,0.9)'
    }}>
      {icon}
    </div>
    <span style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-secondary)' }}>{label}</span>
  </div>
);

export default VisualHub;
