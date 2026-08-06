import { spineFetch } from "@/api/client";

export type DeactivatableResourceKind = "policy" | "webhook" | "agent";

const COLLECTION: Record<DeactivatableResourceKind, string> = {
  policy: "policies",
  webhook: "webhooks",
  agent: "agents",
};

export function resourceApiPath(kind: DeactivatableResourceKind, id: string): string {
  return `/v1/${COLLECTION[kind]}/${id}`;
}

export async function deactivateResource(
  kind: DeactivatableResourceKind,
  id: string,
): Promise<void> {
  await spineFetch<{ status: string }>(resourceApiPath(kind, id), { method: "DELETE" });
}

export async function reactivatePolicy(id: string): Promise<void> {
  await spineFetch(resourceApiPath("policy", id), {
    method: "PUT",
    json: { is_active: true },
  });
}

export const DEACTIVATE_CONFIRM: Record<DeactivatableResourceKind, string> = {
  policy:
    "Deactivate this policy? It will no longer apply to intercept requests. You can reactivate it later.",
  webhook: "Deactivate this webhook? Spine will stop sending events to this URL.",
  agent:
    "Deactivate this agent? It will be marked inactive in the dashboard. Existing audit history is kept.",
};
