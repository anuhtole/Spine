import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, spineFetch } from "@/api/client";
import { DeactivateResourceActions } from "@/components/DeactivateResource";
import { useLiveActivity } from "@/contexts/LiveActivityContext";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  decisionBadgeVariant,
  EmptyState,
  Field,
  Input,
  LiveIndicator,
  PageHeader,
  Spinner,
} from "@/components/ui";

type Webhook = {
  id: string;
  org_id: string;
  url: string;
  name: string | null;
  events: string[] | null;
  is_active: boolean;
};

type CreatedWebhook = Webhook & { hmac_key: string };

export function WebhooksPage() {
  const { streamConnected, interceptFeed } = useLiveActivity();
  const [rows, setRows] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [lastSecret, setLastSecret] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const list = await spineFetch<Webhook[]>("/v1/webhooks", { method: "GET" });
      setRows(list);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load webhooks");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLastSecret(null);
    try {
      const created = await spineFetch<CreatedWebhook>("/v1/webhooks", {
        method: "POST",
        json: { url, name: name || null, events: null },
      });
      setLastSecret(created.hmac_key);
      setUrl("");
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Create failed");
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Webhooks"
        description="Register URLs to receive signed JSON on each intercept. Deactivate an endpoint to stop delivery without losing configuration history."
        badge={<LiveIndicator live={streamConnected} />}
      />

      <Card>
        <CardHeader
          title="Live decision feed"
          subtitle="A preview of the events your webhook endpoints receive in real time."
        />
        {interceptFeed.length === 0 ? (
          <p className="px-6 py-4 text-sm text-spine-muted">
            Decisions will appear here as your agents call Spine.
          </p>
        ) : (
          <ul className="max-h-64 divide-y divide-spine-border overflow-y-auto">
            {interceptFeed.slice(0, 12).map((e) => (
              <li key={e.id} className="flex items-center justify-between gap-3 px-6 py-3 text-sm">
                <span className="font-mono text-xs text-spine-fg">{e.action_type}</span>
                <Badge variant={decisionBadgeVariant(e.decision)}>{e.decision}</Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="max-w-xl">
        <CardHeader title="Add endpoint" />
        <CardBody>
          <form onSubmit={onCreate} className="space-y-4">
            <Field label="Endpoint URL">
              <Input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="font-mono text-xs"
                placeholder="https://your-app.com/webhooks/spine"
                required
              />
            </Field>
            <Field label="Label">
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="production-siem" />
            </Field>
            <Button type="submit">Create webhook</Button>
          </form>
        </CardBody>
      </Card>

      {lastSecret ? (
        <Alert variant="warning">
          <p className="font-medium">Signing secret — copy now</p>
          <p className="mt-1 text-xs opacity-90">This key is only shown once. Store it securely.</p>
          <code className="mt-3 block break-all font-mono text-xs">{lastSecret}</code>
        </Alert>
      ) : null}

      {error ? <Alert variant="error">{error}</Alert> : null}

      <Card>
        <CardHeader title="Endpoints" />
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner className="h-6 w-6" />
          </div>
        ) : rows.length === 0 ? (
          <EmptyState title="No webhooks" description="Add an endpoint to receive decision events." />
        ) : (
          <ul className="divide-y divide-spine-border">
            {rows.map((w) => (
              <li key={w.id} className="flex items-start justify-between gap-4 px-6 py-4">
                <div className="min-w-0">
                  <p className="font-medium text-spine-fg">{w.name ?? "Unnamed"}</p>
                  <p className="mt-0.5 truncate font-mono text-xs text-spine-muted">{w.url}</p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
                  <Badge variant={w.is_active ? "success" : "muted"}>
                    {w.is_active ? "Active" : "Inactive"}
                  </Badge>
                  <DeactivateResourceActions
                    kind="webhook"
                    id={w.id}
                    label={w.name ?? w.url}
                    isActive={w.is_active}
                    onChanged={load}
                    onError={setError}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
