import { useState } from "react";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui";
import {
  DEACTIVATE_CONFIRM,
  deactivateResource,
  reactivatePolicy,
  type DeactivatableResourceKind,
} from "@/lib/resources";

export function DeactivateResourceActions({
  kind,
  id,
  label,
  isActive,
  onChanged,
  onError,
}: {
  kind: DeactivatableResourceKind;
  id: string;
  label: string;
  isActive: boolean;
  onChanged: () => void | Promise<void>;
  onError?: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);

  async function deactivate() {
    const name = label.trim() || id;
    if (!window.confirm(`${DEACTIVATE_CONFIRM[kind]}\n\n${name}`)) return;
    setBusy(true);
    try {
      await deactivateResource(kind, id);
      await onChanged();
    } catch (e) {
      onError?.(e instanceof ApiError ? e.message : "Deactivate failed");
    } finally {
      setBusy(false);
    }
  }

  async function reactivate() {
    if (kind !== "policy") return;
    const name = label.trim() || id;
    if (!window.confirm(`Reactivate policy "${name}"? It will apply to intercept requests again.`)) return;
    setBusy(true);
    try {
      await reactivatePolicy(id);
      await onChanged();
    } catch (e) {
      onError?.(e instanceof ApiError ? e.message : "Reactivate failed");
    } finally {
      setBusy(false);
    }
  }

  if (!isActive) {
    if (kind !== "policy") return null;
    return (
      <Button type="button" size="sm" variant="secondary" disabled={busy} onClick={() => void reactivate()}>
        Reactivate
      </Button>
    );
  }

  return (
    <Button type="button" size="sm" variant="danger" disabled={busy} onClick={() => void deactivate()}>
      Deactivate
    </Button>
  );
}
