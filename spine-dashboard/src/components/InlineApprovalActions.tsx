/**
 * Reusable inline Allow/Block buttons for an approval.
 *
 * Used in the Audit page (next to flagged rows) and the Session detail
 * timeline (next to divergent verdicts that opened an approval).
 *
 * The buttons call POST /v1/approvals/{id}/decide. Auth flows through the
 * BFF's session-cookie → JWT path; the BFF auto-injects org_id for routes
 * under /v1/approvals.
 */
import { useState } from "react";

import { ApiError, spineFetch } from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";

export function InlineApprovalActions({
  approvalId,
  onDecided,
  compact = false,
}: {
  approvalId: string;
  onDecided?: (status: "approved" | "rejected") => void;
  compact?: boolean;
}) {
  const { user } = useAuth();
  const [pending, setPending] = useState<null | "approve" | "reject">(null);
  const [done, setDone] = useState<null | "approved" | "rejected">(null);
  const [error, setError] = useState<string | null>(null);

  // Only org admins can decide. Hide entirely for non-admins — the BFF
  // would 403 the request anyway and we don't want to flash buttons that
  // can't be used.
  if (user?.role !== "admin") return null;

  if (done) {
    return (
      <span
        className={
          done === "approved"
            ? "text-2xs text-emerald-300"
            : "text-2xs text-rose-300"
        }
      >
        {done}
      </span>
    );
  }

  const decide = async (action: "approve" | "reject") => {
    setPending(action);
    setError(null);
    try {
      await spineFetch(`/v1/approvals/${approvalId}/decide`, {
        method: "POST",
        json: {
          action,
          decided_by: user?.email || user?.name || "dashboard",
        },
      });
      const newStatus = action === "approve" ? "approved" : "rejected";
      setDone(newStatus);
      onDecided?.(newStatus);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed");
    } finally {
      setPending(null);
    }
  };

  const sizeClass = compact ? "px-1.5 py-0.5 text-2xs" : "px-2.5 py-1 text-xs";

  return (
    <span className="inline-flex items-center gap-1.5">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          void decide("approve");
        }}
        disabled={pending !== null}
        className={`rounded font-medium bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 disabled:opacity-40 ${sizeClass}`}
        title="Allow this action — agent can retry"
      >
        {pending === "approve" ? "…" : "Allow"}
      </button>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          void decide("reject");
        }}
        disabled={pending !== null}
        className={`rounded font-medium bg-rose-500/15 text-rose-300 hover:bg-rose-500/25 disabled:opacity-40 ${sizeClass}`}
        title="Block this action"
      >
        {pending === "reject" ? "…" : "Block"}
      </button>
      {error ? <span className="text-2xs text-rose-300">{error}</span> : null}
    </span>
  );
}
