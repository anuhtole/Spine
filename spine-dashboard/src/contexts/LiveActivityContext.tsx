import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { spineFetch } from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";
import { useSpineActivityStream, type SpineStreamMessage } from "@/hooks/useSpineActivityStream";

export type PendingApproval = {
  id: string;
  agent_id: string;
  action_type: string;
  target_resource: string | null;
  reason: string | null;
  ts: string;
};

export type InterceptFeedItem = {
  id: string;
  agent_id: string;
  action_type: string;
  target_resource: string | null;
  decision: string;
  ts: string;
};

type LiveActivityContextValue = {
  streamConnected: boolean;
  streamError: string | null;
  pendingApprovals: PendingApproval[];
  pendingCount: number;
  interceptFeed: InterceptFeedItem[];
  dismissApproval: (id: string) => void;
  decideApproval: (id: string, action: "approve" | "reject") => Promise<void>;
};

const LiveActivityContext = createContext<LiveActivityContextValue | null>(null);

function parseApprovalPending(msg: SpineStreamMessage): PendingApproval | null {
  if (msg.data.status !== "pending") return null;
  const id = String(msg.data.id ?? "");
  if (!id) return null;
  return {
    id,
    agent_id: String(msg.data.agent_id ?? ""),
    action_type: String(msg.data.action_type ?? "action"),
    target_resource:
      msg.data.target_resource != null ? String(msg.data.target_resource) : null,
    reason: msg.data.reason != null ? String(msg.data.reason) : null,
    ts: msg.ts,
  };
}

export function LiveActivityProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(() => new Set());
  const [interceptFeed, setInterceptFeed] = useState<InterceptFeedItem[]>([]);

  const onEvent = useCallback(
    (msg: SpineStreamMessage) => {
      if (msg.type === "audit") {
        const d = msg.data;
        const row: InterceptFeedItem = {
          id: String(d.id),
          agent_id: String(d.agent_id),
          action_type: String(d.action_type),
          target_resource: d.target_resource != null ? String(d.target_resource) : null,
          decision: String(d.policy_decision ?? "—"),
          ts: msg.ts,
        };
        setInterceptFeed((prev) => {
          if (prev.some((e) => e.id === row.id)) return prev;
          return [row, ...prev].slice(0, 30);
        });
        return;
      }

      if (msg.type === "approval") {
        const status = String(msg.data.status ?? "");
        const id = String(msg.data.id ?? "");
        if (!id) return;
        if (status === "pending" && user?.role === "admin") {
          const item = parseApprovalPending(msg);
          if (!item || dismissed.has(id)) return;
          setPendingApprovals((prev) => {
            if (prev.some((p) => p.id === id)) return prev;
            return [item, ...prev].slice(0, 20);
          });
        } else {
          setPendingApprovals((prev) => prev.filter((p) => p.id !== id));
        }
      }
    },
    [dismissed, user?.role],
  );

  const { connected: streamConnected, error: streamError } = useSpineActivityStream(
    onEvent,
    Boolean(user),
  );

  useEffect(() => {
    if (!user?.org_id || user.role !== "admin") return;
    spineFetch<
      Array<{
        id: string;
        agent_id: string;
        proposed: Record<string, unknown>;
      }>
    >(`/v1/approvals?org_id=${encodeURIComponent(user.org_id)}&status_filter=pending`)
      .then((list) => {
        const mapped: PendingApproval[] = list.map((row) => {
          const action = row.proposed?.action as Record<string, unknown> | undefined;
          return {
            id: row.id,
            agent_id: row.agent_id,
            action_type: String(action?.action_type ?? "action"),
            target_resource:
              action?.target_resource != null ? String(action.target_resource) : null,
            reason: null,
            ts: new Date().toISOString(),
          };
        });
        setPendingApprovals(mapped);
      })
      .catch(() => {});
  }, [user?.org_id, user?.role]);

  const dismissApproval = useCallback((id: string) => {
    setDismissed((prev) => new Set(prev).add(id));
    setPendingApprovals((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const decideApproval = useCallback(
    async (id: string, action: "approve" | "reject") => {
      if (!user?.org_id) return;
      await spineFetch(`/v1/approvals/${id}/decide?org_id=${encodeURIComponent(user.org_id)}`, {
        method: "POST",
        json: { action, decided_by: user.name || user.email },
      });
      setPendingApprovals((prev) => prev.filter((p) => p.id !== id));
    },
    [user],
  );

  const visiblePending = pendingApprovals.filter((p) => !dismissed.has(p.id));

  const value = useMemo(
    () => ({
      streamConnected,
      streamError,
      pendingApprovals: visiblePending,
      pendingCount: visiblePending.length,
      interceptFeed,
      dismissApproval,
      decideApproval,
    }),
    [
      streamConnected,
      streamError,
      visiblePending,
      interceptFeed,
      dismissApproval,
      decideApproval,
    ],
  );

  return <LiveActivityContext.Provider value={value}>{children}</LiveActivityContext.Provider>;
}

export function useLiveActivity() {
  const ctx = useContext(LiveActivityContext);
  if (!ctx) {
    throw new Error("useLiveActivity must be used within LiveActivityProvider");
  }
  return ctx;
}

export function useLiveActivityOptional() {
  return useContext(LiveActivityContext);
}
