import { FormEvent, useState } from "react";
import { ApiError, spineFetch } from "@/api/client";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  Field,
  Input,
  PageHeader,
} from "@/components/ui";

type Org = { id: string; name: string; plan: string };
type KeyCreated = { id: string; org_id: string; name: string | null; raw_key: string };

export function OrgsPage() {
  const [error, setError] = useState<string | null>(null);
  const [orgName, setOrgName] = useState("");
  const [plan, setPlan] = useState("starter");
  const [createdOrg, setCreatedOrg] = useState<Org | null>(null);

  const [orgIdForKey, setOrgIdForKey] = useState("");
  const [keyName, setKeyName] = useState("local-dev");
  const [createdKey, setCreatedKey] = useState<KeyCreated | null>(null);

  async function createOrg(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCreatedOrg(null);
    try {
      const o = await spineFetch<Org>("/v1/orgs", {
        method: "POST",
        json: { name: orgName, plan },
      });
      setCreatedOrg(o);
      setOrgIdForKey(o.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Create org failed");
    }
  }

  async function mintKey(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCreatedKey(null);
    if (!orgIdForKey.trim()) {
      setError("Organization ID is required");
      return;
    }
    try {
      const k = await spineFetch<KeyCreated>(`/v1/orgs/${orgIdForKey.trim()}/api-keys`, {
        method: "POST",
        json: { name: keyName || null },
      });
      setCreatedKey(k);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Mint key failed");
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Organizations"
        description="Platform administration: create tenants and mint org-scoped API keys for SDK access."
      />

      <Alert variant="info">
        <p className="font-medium">Restricted to platform administrators</p>
        <p className="mt-1 text-xs opacity-90">
          Your account must be listed in{" "}
          <code className="code-inline">BFF_PLATFORM_ADMIN_EMAILS</code> on the dashboard server.
          API keys are shown once — store them securely.
        </p>
      </Alert>

      {error ? (
        <Alert variant="error">
          <p>{error}</p>
        </Alert>
      ) : null}

      <Card>
        <CardHeader title="Create organization" subtitle="Bootstrap a new tenant." />
        <CardBody>
          <form onSubmit={createOrg} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Name">
                <Input value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
              </Field>
              <Field label="Plan">
                <Input value={plan} onChange={(e) => setPlan(e.target.value)} />
              </Field>
            </div>
            <Button type="submit">Create organization</Button>
          </form>
          {createdOrg ? (
            <div className="mt-5 rounded-lg border border-spine-border bg-spine-elevated/50 p-4 text-sm">
              <p className="text-2xs font-medium uppercase tracking-wider text-spine-subtle">Created</p>
              <p className="mt-1 font-mono text-xs text-spine-muted">{createdOrg.id}</p>
              <p className="mt-1 text-spine-fg">
                {createdOrg.name} · {createdOrg.plan}
              </p>
            </div>
          ) : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Mint org API key" subtitle="Raw key is returned once." />
        <CardBody>
          <form onSubmit={mintKey} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Organization ID">
                <Input
                  value={orgIdForKey}
                  onChange={(e) => setOrgIdForKey(e.target.value)}
                  className="font-mono"
                  required
                />
              </Field>
              <Field label="Key name">
                <Input value={keyName} onChange={(e) => setKeyName(e.target.value)} />
              </Field>
            </div>
            <Button type="submit" variant="secondary">
              Mint API key
            </Button>
          </form>
          {createdKey ? (
            <div className="mt-5">
              <Alert variant="warning">
                <p className="font-medium">raw_key (shown once)</p>
                <code className="mt-2 block break-all font-mono text-xs">{createdKey.raw_key}</code>
              </Alert>
            </div>
          ) : null}
        </CardBody>
      </Card>
    </div>
  );
}
