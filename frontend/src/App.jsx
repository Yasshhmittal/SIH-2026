/**
 * PRAHARÍ — Main Application
 * Sovereign Industrial AI Workbench
 * 
 * Orchestrates the full UI: sidebar navigation, task input,
 * live agent timeline (via WebSocket), right panel with model/sources/artifact,
 * and security status.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';

import Header from './components/Header';
import Sidebar from './components/Sidebar';
import TaskInput from './components/TaskInput';
import AgentTimeline from './components/AgentTimeline';
import RightPanel from './components/RightPanel';
import AnalysisResults from './components/AnalysisResults';

const API_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

export default function App() {
  // ── State ────────────────────────────────────────────────────────────────
  const [activeWorkflow, setActiveWorkflow] = useState('inspection');
  const [taskText, setTaskText] = useState('');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState([]);

  // Right panel & results state
  const [profile, setProfile] = useState(null);
  const [sources, setSources] = useState([]);
  const [artifact, setArtifact] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [validation, setValidation] = useState(null);
  const [securityStatus, setSecurityStatus] = useState(null);
  const [egressResult, setEgressResult] = useState(null);
  const [isTestingEgress, setIsTestingEgress] = useState(false);

  // WebSocket ref
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);

  // ── WebSocket Connection ─────────────────────────────────────────────────
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('[WS] Connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleAgentEvent(data);
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };

      ws.onclose = () => {
        console.log('[WS] Disconnected, reconnecting in 3s...');
        reconnectTimerRef.current = setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (err) => {
        console.log('[WS] Error, will reconnect...');
        ws.close();
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      reconnectTimerRef.current = setTimeout(connectWebSocket, 3000);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();
    fetchSecurityStatus();

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    };
  }, [connectWebSocket]);

  // ── Handle Agent Events ──────────────────────────────────────────────────
  const handleAgentEvent = (event) => {
    // Add to timeline, resolving previous 'started' spinners
    setEvents((prev) => {
      if (event.status === 'completed' || event.status === 'failed' || event.status === 'error') {
        const existingStartedIdx = prev.findIndex(e => e.step === event.step && e.status === 'started');
        if (existingStartedIdx >= 0) {
          const newEvents = [...prev];
          newEvents[existingStartedIdx] = { ...newEvents[existingStartedIdx], status: 'completed' };
          return [...newEvents, event];
        }
      }
      return [...prev, event];
    });

    // Extract data for right panel
    if (event.data?.profile && typeof event.data.profile === 'object' && event.data.profile.name) {
      setProfile(event.data.profile);
    }
    if (event.data?.sources) {
      setSources(event.data.sources);
    }
    if (event.data?.artifact) {
      setArtifact(event.data.artifact);
    }
    if (event.data?.analysis) {
      setAnalysis(event.data.analysis);
    }
    if (event.data?.validation) {
      setValidation(event.data.validation);
    }

    // Check for pipeline completion
    if (event.step === 'complete' || event.status === 'error') {
      setIsRunning(false);
      fetchSecurityStatus();
    }
  };

  // ── API Calls ────────────────────────────────────────────────────────────
  const fetchSecurityStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/security/status`);
      if (res.ok) {
        const data = await res.json();
        setSecurityStatus(data);
      }
    } catch (e) {
      console.log('[API] Security status fetch failed (backend may not be running)');
    }
  };

  const runAgent = async () => {
    // Clear previous state
    setEvents([]);
    setProfile(null);
    setSources([]);
    setArtifact(null);
    setAnalysis(null);
    setValidation(null);
    setIsRunning(true);

    try {
      const formData = new FormData();
      formData.append('task_description', taskText);
      if (uploadedFile) {
        formData.append('file', uploadedFile);
      }

      const endpoint = activeWorkflow === 'coding' ? '/task/coding' : '/task';
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }

      const data = await res.json();
      console.log('[API] Task submitted:', data);
    } catch (e) {
      console.error('[API] Error:', e);
      setIsRunning(false);
      setEvents((prev) => [
        ...prev,
        {
          type: 'error',
          step: 'connection',
          status: 'error',
          message: `Failed to connect to backend: ${e.message}. Make sure the backend is running on port 8000.`,
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  };

  const runEgressTest = async () => {
    setIsTestingEgress(true);
    try {
      const res = await fetch(`${API_BASE}/security/egress-test`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setEgressResult(data);
      }
    } catch (e) {
      console.error('[API] Egress test error:', e);
    }
    setIsTestingEgress(false);
    fetchSecurityStatus();
  };

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="app-layout">
      <Header securityStatus={securityStatus} />

      <main className="app-main">
        <Sidebar
          activeWorkflow={activeWorkflow}
          onSelectWorkflow={(wf) => {
            setActiveWorkflow(wf);
            setEvents([]);
            setProfile(null);
            setSources([]);
            setArtifact(null);
            setAnalysis(null);
            setValidation(null);
          }}
        />

        <div className="main-content">
          <TaskInput
            activeWorkflow={activeWorkflow}
            taskText={taskText}
            onTaskTextChange={setTaskText}
            uploadedFile={uploadedFile}
            onFileUpload={setUploadedFile}
            onRunAgent={runAgent}
            isRunning={isRunning}
          />

          <AnalysisResults analysis={analysis} validation={validation} />

          <AgentTimeline events={events} />
        </div>

        <RightPanel
          profile={profile}
          sources={sources}
          artifact={artifact}
          securityStatus={securityStatus}
          onEgressTest={runEgressTest}
          egressResult={egressResult}
          isTestingEgress={isTestingEgress}
        />
      </main>
    </div>
  );
}
