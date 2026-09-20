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
  // Conversation history: array of {role: "user"|"assistant", content: string}
  const [history, setHistory] = useState([]);
  // Track whether we already captured the answer for the current run
  const [answerCaptured, setAnswerCaptured] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length, history.length]);

  // Watch for run.completed events and capture the answer into history
  useEffect(() => {
    if (answerCaptured) return;
    const completed = events.find(e => e.type === "run.completed");
    if (completed && currentPrompt) {
      const answer = completed.payload?.answer || "(No text answer — see deliverable above)";
      setHistory(prev => [
        ...prev,
        { role: "user", content: currentPrompt },
        { role: "assistant", content: answer },
      ]);
      setAnswerCaptured(true);
    }
  }, [events, currentPrompt, answerCaptured]);

  const handleSubmit = useCallback(
    async (prompt) => {
      try {
        reset();
        setCurrentPrompt(prompt);
        setAnswerCaptured(false);
        const { run_id } = await apiPost("/api/runs", {
          prompt,
          history,
        });
        startStream(run_id);
      } catch (err) {
        console.error("Failed to start run:", err);
      }
    },
    [reset, startStream, history]
  );

  const handleNewThread = useCallback(() => {
    reset();
    setCurrentPrompt("");
    setHistory([]);
    setAnswerCaptured(false);
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
              {/* Welcome screen — only when no history and no active prompt */}
              {history.length === 0 && events.length === 0 && !currentPrompt && (
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

              {/* Past conversation history */}
              {history.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: '1rem 0' }}>
                  {history.map((msg, i) => (
                    <div
                      key={`hist-${i}`}
                      style={{
                        display: 'flex',
                        justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      }}
                    >
                      <div
                        className="glass"
                        style={{
                          padding: '0.75rem 1rem',
                          maxWidth: '75%',
                          borderRadius: msg.role === 'user' ? '1rem 1rem 0.25rem 1rem' : '1rem 1rem 1rem 0.25rem',
                          background: msg.role === 'user'
                            ? 'rgba(139, 92, 246, 0.15)'
                            : 'var(--glass-bg)',
                          border: msg.role === 'user'
                            ? '1px solid rgba(139, 92, 246, 0.3)'
                            : '1px solid var(--glass-border)',
                          fontSize: '0.85rem',
                          color: 'var(--text-primary)',
                          whiteSpace: 'pre-wrap',
                          lineHeight: '1.5',
                        }}
                      >
                        <div style={{
                          fontSize: '0.65rem',
                          fontWeight: 600,
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                          color: msg.role === 'user' ? 'rgba(139, 92, 246, 0.8)' : 'rgba(16, 185, 129, 0.8)',
                          marginBottom: '0.35rem',
                        }}>
                          {msg.role === 'user' ? 'You' : 'Prahari'}
                        </div>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  {/* Divider between history and active run */}
                  {currentPrompt && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', margin: '0.5rem 0' }}>
                      <div style={{ flex: 1, height: '1px', background: 'var(--glass-border)' }} />
                      <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Current Run</span>
                      <div style={{ flex: 1, height: '1px', background: 'var(--glass-border)' }} />
                    </div>
                  )}
                </div>
              )}

              {/* Active run prompt */}
              {currentPrompt && !answerCaptured && (
                <div className="glass" style={{ padding: '1rem', marginBottom: '1rem', background: 'rgba(139, 92, 246, 0.1)', border: '1px solid rgba(139, 92, 246, 0.25)' }}>
                  <div style={{
                    fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase',
                    letterSpacing: '0.05em', color: 'rgba(139, 92, 246, 0.8)', marginBottom: '0.35rem',
                  }}>You</div>
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
