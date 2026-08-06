import { useCallback, useEffect, useState } from "react";
import { ApiError, spineFetch } from "@/api/client";
import { InlineApprovalActions } from "@/components/InlineApprovalActions";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  decisionBadgeVariant,
  EmptyState,
  LiveIndicator,
  PageHeader,
  Spinner,
} from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { useSpineActivityStream } from "@/hooks/useSpineActivityStream";

type AuditEvent = {
  id: string;
  agent_id: string;
  org_id: string;
  action_type: string;
  target_resource: string | null;
  policy_decision: string | null;
  policy_id: string | null;
  metadata: Record<string, unknown> | null;
};

type VerifyResult = {
  ok: boolean;
  org_id: string;
  checked: number;
  first_bad_sequence: number | null;
  error: string | null;
};

type Approval = {
  id: string;
  agent_id: string;
  audit_event_id: string | null;
  status: string;
};

export function AuditPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [verify, setVerify] = useState<VerifyResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // audit_event_id → approval_id for pending approvals (admin only)
  const [pendingApprovals, setPendingApprovals] = useState<Record<string, string>>({});

  const { connected: streamLive } = useSpineActivityStream((msg) => {
    if (msg.type !== "audit") return;
    const d = msg.data;
    const row: AuditEvent = {
      id: String(d.id),
      agent_id: String(d.agent_id),
      org_id: String(d.org_id),
      action_type: String(d.action_type),
      target_resource: d.target_resource != null ? String(d.target_resource) : null,
      policy_decision: d.policy_decision != null ? String(d.policy_decision) : null,
      policy_id: d.policy_id != null ? String(d.policy_id) : null,
      metadata: (d.metadata as Record<string, unknown>) ?? null,
    };
    setEvents((prev) => {
      if (prev.some((e) => e.id === row.id)) return prev;
      return [row, ...prev].slice(0, 50);
    });
  });

  const load = useCallback(async () => {
    setError(null);
    try {
      const rows = await spineFetch<AuditEvent[]>("/v1/audit?limit=50", { method: "GET" });
      setEvents(rows);
      if (isAdmin) {
        const approvals = await spineFetch<Approval[]>(
          "/v1/approvals?status_filter=pending",
          { method: "GET" },
        ).catch(() => [] as Approval[]);
        const map: Record<string, string> = {};
        for (const a of approvals) {
          if (a.audit_event_id) map[a.audit_event_id] = a.id;
        }
        setPendingApprovals(map);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load audit");
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    void load();
  }, [load]);

  async function runVerify() {
    setError(null);
    setVerify(null);
    try {
      const r = await spineFetch<VerifyResult>("/v1/audit/verify", { method: "GET" });
      setVerify(r);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Verify failed");
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Audit log"
        description="Tamper-evident record of every policy decision. Verify chain integrity at any time."
        badge={<LiveIndicator live={streamLive} />}
        actions={
          <>
            <Button variant="secondary" size="sm" onClick={() => void load()}>
              Refresh
            </Button>
            <Button size="sm" onClick={() => void runVerify()}>
              Verify chain
            </Button>
          </>
        }
      />

      {error ? <Alert variant="error">{error}</Alert> : null}

      {verify ? (
        <Alert variant={verify.ok ? "success" : "error"}>
          <p className="font-medium">{verify.ok ? "Chain integrity verified" : "Chain integrity issue"}</p>
          <p className="mt-1 font-mono text-xs opacity-90">
            checked={verify.checked} · first_bad={String(verify.first_bad_sequence)} · error=
            {verify.error ?? "none"}
          </p>
        </Alert>
      ) : null}

      <Card>
        <CardHeader title="Events" subtitle="Most recent first" />
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner className="h-6 w-6" />
          </div>
        ) : events.length === 0 ? (
          <EmptyState
            title="No audit events"
            description="Run an intercept to create your first tamper-evident record."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Action</th>
                  <th>Decision</th>
                  <th>Target</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td className="max-w-[140px] font-mono text-2xs break-all">{ev.id}</td>
                    <td className="text-spine-fg">{ev.action_type}</td>
                    <td>
                      <div className="inline-flex items-center gap-2">
                        <Badge variant={decisionBadgeVariant(ev.policy_decision)}>
                          {ev.policy_decision ?? "—"}
                        </Badge>
                        {ev.policy_decision === "flagged" && pendingApprovals[ev.id] ? (
                          <InlineApprovalActions
                            approvalId={pendingApprovals[ev.id]}
                            compact
                            onDecided={() => {
                              // Remove from pending map so buttons disappear
                              setPendingApprovals((m) => {
                                const next = { ...m };
                                delete next[ev.id];
                                return next;
                              });
                            }}
                          />
                        ) : null}
                      </div>
                    </td>
                    <td className="max-w-[200px] truncate font-mono text-xs">
                      {ev.target_resource ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
