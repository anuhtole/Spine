import { useEffect, useRef, useState } from "react";

export type StreamEventType =
  | "connected"
  | "audit"
  | "approval"
  | "heartbeat"
  | "plan_evaluation"
  | "plan_drift";

export type SpineStreamMessage = {
  type: StreamEventType;
  org_id: string;
  ts: string;
  data: Record<string, unknown>;
};

type Handler = (msg: SpineStreamMessage) => void;

export function useSpineActivityStream(onEvent: Handler, enabled = true) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    if (!enabled) return;

    const es = new EventSource("/api/spine/v1/audit/stream", { withCredentials: true });

    es.onopen = () => {
      setConnected(true);
      setError(null);
    };

    es.onerror = () => {
      setConnected(false);
      setError("Activity stream disconnected");
    };

    const listen = (eventType: string) => {
      es.addEventListener(eventType, (ev) => {
        try {
          const data = JSON.parse((ev as MessageEvent).data) as SpineStreamMessage;
          handlerRef.current(data);
        } catch {
          /* ignore malformed */
        }
      });
    };

    for (const t of [
      "connected",
      "audit",
      "approval",
      "heartbeat",
      "plan_evaluation",
      "plan_drift",
    ]) {
      listen(t);
    }

    return () => {
      es.close();
      setConnected(false);
    };
  }, [enabled]);

  return { connected, error };
}
