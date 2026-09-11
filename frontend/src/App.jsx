import React from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import VisualHub from './components/VisualHub';
import StatsCards from './components/StatsCards';
import './index.css';

function App() {
  return (
    <>
      <div className="pattern-bg"></div>
      <div className="glow-bg"></div>
      
      <div className="app-container">
        <Navbar />
        
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '4rem', position: 'relative' }}>
          <Hero />
          <VisualHub />
        </main>
        
        <StatsCards />
      </div>
    </>
  );
}

export default App;
