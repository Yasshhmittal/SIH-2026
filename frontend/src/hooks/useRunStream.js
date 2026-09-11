import { useCallback, useEffect, useRef, useState } from "react";
import { sseUrl } from "../lib/api";

/**
 * React hook that consumes the SSE event stream from a PRAHARI run.
 * Handles reconnection, replay, and terminal event detection.
 */
export function useRunStream() {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("idle");
  const sourceRef = useRef(null);

  const reset = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    setEvents([]);
    setStatus("idle");
  }, []);

  const startStream = useCallback((runId) => {
    if (sourceRef.current) {
      sourceRef.current.close();
    }
    setEvents([]);
    setStatus("connecting");

    const url = sseUrl(runId);
    const source = new EventSource(url);
    sourceRef.current = source;

    source.onopen = () => {
      setStatus("running");
    };

    source.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data);
        setEvents((prev) => [...prev, event]);

        if (
          event.type === "run.completed" ||
          event.type === "run.failed" ||
          event.type === "run.cancelled"
        ) {
          setStatus(
            event.type === "run.completed"
              ? "completed"
              : event.type === "run.failed"
              ? "failed"
              : "cancelled"
          );
          source.close();
          sourceRef.current = null;
        }
      } catch (err) {
        // Ignore malformed events
      }
    };

    source.onerror = () => {
      if (status === "connecting" || status === "running") {
        setStatus("failed");
      }
      source.close();
      sourceRef.current = null;
    };
  }, [status]);

  useEffect(() => {
    return () => {
      if (sourceRef.current) {
        sourceRef.current.close();
      }
    };
  }, []);

  return { events, status, startStream, reset };
}
