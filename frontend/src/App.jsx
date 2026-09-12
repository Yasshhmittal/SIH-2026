import React, { useCallback, useRef, useEffect, useState } from 'react';
import TopBar from './components/TopBar';
import Sidebar from './components/Sidebar';
import Timeline from './components/Timeline';
import Inspector from './components/Inspector';
import PromptInput from './components/PromptInput';
import { useRunStream } from './hooks/useRunStream';
import { apiPost } from './lib/api';
import './index.css';

function App() {
  const { events, status, runId, startStream, reset } = useRunStream();
  const [currentPrompt, setCurrentPrompt] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  const handleSubmit = useCallback(
    async (prompt) => {
      try {
        reset();
        setCurrentPrompt(prompt);
        const { run_id } = await apiPost("/api/runs", { prompt });
        startStream(run_id);
      } catch (err) {
        console.error("Failed to start run:", err);
      }
    },
    [reset, startStream]
  );

  const handleNewThread = useCallback(() => {
    reset();
    setCurrentPrompt("");
  }, [reset]);

  const isRunning = status === "running" || status === "connecting";

  return (
    <>
      <div className="pattern-bg"></div>
      <div className="glow-bg"></div>
      
      <div className="app-container" style={{ padding: 0, height: '100vh', display: 'flex', flexDirection: 'column' }}>
        <TopBar />
        
        <div style={{ flex: 1, display: 'flex', gap: '1rem', padding: '0 1.5rem 1.5rem 1.5rem', overflow: 'hidden' }}>
          {/* Sidebar */}
          <div style={{ width: '240px', flexShrink: 0 }}>
            <Sidebar onNewThread={handleNewThread} />
          </div>

          {/* Main Chat Area */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', paddingRight: '0.5rem' }}>
              {events.length === 0 && !currentPrompt && (
                <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}>
                  <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🛡️</div>
                  <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.5rem' }}>Welcome to PRAHARI</h2>
                  <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>AI comes to your data — not the other way around.</p>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%', maxWidth: '500px' }}>
                    {[
                      "Draft an approval note for the thickness deficiency found at Elbow E-14 on line 8-P-1204",
                      "What is the minimum retirement thickness for 8 inch CS piping in sour service?",
                      "Write a Python script to compute corrosion rate from inspection CSV data"
                    ].map((example, i) => (
                      <button
                        key={i}
                        onClick={() => handleSubmit(example)}
                        className="glass"
                        style={{ padding: '1rem', textAlign: 'left', border: 'none', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-secondary)' }}
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {currentPrompt && (
                <div className="glass" style={{ padding: '1rem', marginBottom: '1rem', background: 'var(--glass-bg)' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 500 }}>{currentPrompt}</div>
                </div>
              )}

              {events.length > 0 && <Timeline events={events} runId={runId} />}
              
              {isRunning && (
                <div style={{ display: 'flex', gap: '0.5rem', padding: '1rem', alignItems: 'center' }}>
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-color)', animation: 'pulse 1s infinite' }} />
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-color)', animation: 'pulse 1s infinite 0.2s' }} />
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-color)', animation: 'pulse 1s infinite 0.4s' }} />
                </div>
              )}
            </div>
            
            <PromptInput onSubmit={handleSubmit} disabled={isRunning} status={status} />
          </div>

          {/* Inspector */}
          <div style={{ width: '320px', flexShrink: 0 }}>
            <Inspector events={events} />
          </div>
        </div>
      </div>
    </>
  );
}

export default App;
