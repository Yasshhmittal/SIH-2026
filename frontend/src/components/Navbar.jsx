import React from 'react';
import { ShieldAlert, DownloadCloud } from 'lucide-react';

const Navbar = () => {
  return (
    <nav style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '1.5rem 0',
      width: '100%',
      zIndex: 10
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '1.25rem' }}>
        <div style={{
          width: '32px', height: '32px', borderRadius: '8px', 
          background: 'linear-gradient(135deg, #2c2d33 0%, #0b0c10 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'white'
        }}>
          <ShieldAlert size={18} />
        </div>
        PRAHARI
      </div>

      {/* Links */}
      <div className="glass" style={{
        display: 'flex',
        gap: '2rem',
        padding: '0.5rem 2rem',
        borderRadius: '9999px',
        fontSize: '0.9rem',
        fontWeight: 500,
        color: 'var(--text-secondary)'
      }}>
        <a href="#home" style={{ color: 'var(--text-primary)', textDecoration: 'none' }}>Home</a>
        <a href="#architecture" style={{ color: 'inherit', textDecoration: 'none' }}>Architecture</a>
        <a href="#features" style={{ color: 'inherit', textDecoration: 'none' }}>Features</a>
        <a href="#security" style={{ color: 'inherit', textDecoration: 'none' }}>Security</a>
        <a href="#models" style={{ color: 'inherit', textDecoration: 'none' }}>Models</a>
      </div>

      {/* CTA */}
      <button className="btn btn-primary" style={{ gap: '0.5rem' }}>
        Deploy Local <DownloadCloud size={16} />
      </button>
    </nav>
  );
};

export default Navbar;
