import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, spineFetch } from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  Field,
  Input,
  PageHeader,
  Select,
  Spinner,
} from "@/components/ui";

type Member = {
  user_id: string;
  email: string;
  name: string;
  role: string;
  created_at: string;
};

type ApiKeyRow = {
  id: string;
  org_id: string;
  name: string | null;
  created_at: string;
  revoked_at: string | null;
  is_active: boolean;
};

type KeyCreated = {
  id: string;
  org_id: string;
  name: string | null;
  raw_key: string;
};

export function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [members, setMembers] = useState<Member[]>([]);
  const [keys, setKeys] = useState<ApiKeyRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [invitePassword, setInvitePassword] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [keyName, setKeyName] = useState("sdk");
  const [createdKey, setCreatedKey] = useState<KeyCreated | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const load = useCallback(async () => {
    if (!isAdmin) {
      setLoading(false);
      return;
    }
    setError(null);
    try {
      const [m, k] = await Promise.all([
        spineFetch<Member[]>("/v1/members"),
        spineFetch<ApiKeyRow[]>("/v1/api-keys"),
      ]);
      setMembers(m);
      setKeys(k);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    void load();
  }, [load]);

  async function inviteMember(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      await spineFetch<Member>("/v1/members", {
        method: "POST",
        json: {
          email: inviteEmail.trim(),
          name: inviteName.trim(),
          password: invitePassword,
          role: inviteRole,
        },
      });
      setSuccess(`Added ${inviteEmail} to your organization.`);
      setInviteEmail("");
      setInviteName("");
      setInvitePassword("");
      setInviteRole("member");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add member");
    }
  }

  async function updateRole(userId: string, role: string) {
    setError(null);
    setSuccess(null);
    try {
      await spineFetch<Member>(`/v1/members/${userId}`, {
        method: "PATCH",
        json: { role },
      });
      setSuccess("Role updated.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update role");
    }
  }

  async function removeMember(userId: string, email: string) {
    if (!window.confirm(`Remove ${email} from this organization?`)) return;
    setError(null);
    setSuccess(null);
    try {
      await spineFetch<void>(`/v1/members/${userId}`, { method: "DELETE" });
      setSuccess(`Removed ${email}.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove member");
    }
  }

  async function mintKey(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setCreatedKey(null);
    try {
      const row = await spineFetch<KeyCreated>("/v1/api-keys", {
        method: "POST",
        json: { name: keyName.trim() || null },
      });
      setCreatedKey(row);
      setSuccess("API key created. Copy it now — it won't be shown again.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to mint key");
    }
  }

  async function revokeKey(keyId: string) {
    if (!window.confirm("Revoke this API key? SDK calls using it will fail.")) return;
    setError(null);
    setSuccess(null);
    try {
      await spineFetch<ApiKeyRow>(`/v1/api-keys/${keyId}/revoke`, { method: "POST" });
      setSuccess("Key revoked.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to revoke key");
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }
    try {
      await spineFetch<void>("/v1/auth/change-password", {
        method: "POST",
        json: { current_password: currentPassword, new_password: newPassword },
      });
      setSuccess("Password updated.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to change password");
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Settings"
        description={
          isAdmin
            ? "Manage your team, API keys, and account."
            : "Your account and organization details."
        }
      />

      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success">{success}</Alert> : null}

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardBody>
            <h2 className="text-sm font-medium text-spine-fg">Profile</h2>
            <dl className="mt-4 space-y-4 text-sm">
              <div>
                <dt className="text-2xs uppercase tracking-wider text-spine-subtle">Name</dt>
                <dd className="mt-0.5 text-spine-fg">{user?.name ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-2xs uppercase tracking-wider text-spine-subtle">Email</dt>
                <dd className="mt-0.5 text-spine-fg">{user?.email ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-2xs uppercase tracking-wider text-spine-subtle">Role</dt>
                <dd className="mt-1">
                  <Badge variant="accent">{user?.role ?? "—"}</Badge>
                </dd>
              </div>
            </dl>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <h2 className="text-sm font-medium text-spine-fg">Organization</h2>
            <dl className="mt-4 space-y-4 text-sm">
              <div>
                <dt className="text-2xs uppercase tracking-wider text-spine-subtle">Name</dt>
                <dd className="mt-0.5 text-spine-fg">{user?.org_name ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-2xs uppercase tracking-wider text-spine-subtle">Org ID</dt>
                <dd className="mt-0.5 font-mono text-xs break-all text-spine-muted">
                  {user?.org_id ?? "—"}
                </dd>
              </div>
            </dl>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader title="Change password" />
        <CardBody>
          <form onSubmit={(e) => void changePassword(e)} className="max-w-md space-y-4">
            <Field label="Current password">
              <Input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </Field>
            <Field label="New password">
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </Field>
            <Field label="Confirm new password">
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </Field>
            <Button type="submit">Update password</Button>
          </form>
        </CardBody>
      </Card>

      {isAdmin ? (
        <>
          <Card>
            <CardHeader
              title="Team"
              subtitle="Add dashboard users to your organization. They share agents, policies, and audit data."
            />
            <CardBody className="space-y-6">
              {loading ? (
                <div className="flex justify-center py-8">
                  <Spinner />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Email</th>
                        <th>Name</th>
                        <th>Role</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {members.map((m) => (
                        <tr key={m.user_id}>
                          <td className="text-spine-fg">{m.email}</td>
                          <td>{m.name}</td>
                          <td>
                            <Select
                              value={m.role}
                              onChange={(e) => void updateRole(m.user_id, e.target.value)}
                              className="text-xs py-1"
                              disabled={m.user_id === user?.id}
                            >
                              <option value="admin">admin</option>
                              <option value="member">member</option>
                              <option value="viewer">viewer</option>
                            </Select>
                          </td>
                          <td className="text-right">
                            {m.user_id !== user?.id ? (
                              <Button
                                type="button"
                                variant="ghost"
                                className="text-xs text-red-400"
                                onClick={() => void removeMember(m.user_id, m.email)}
                              >
                                Remove
                              </Button>
                            ) : (
                              <span className="text-2xs text-spine-subtle">you</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <form onSubmit={(e) => void inviteMember(e)} className="border-t border-spine-border pt-6 space-y-4">
                <h3 className="text-sm font-medium text-spine-fg">Add team member</h3>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Email">
                    <Input
                      type="email"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      required
                    />
                  </Field>
                  <Field label="Name">
                    <Input value={inviteName} onChange={(e) => setInviteName(e.target.value)} required />
                  </Field>
                  <Field label="Temporary password">
                    <Input
                      type="password"
                      value={invitePassword}
                      onChange={(e) => setInvitePassword(e.target.value)}
                      required
                      minLength={8}
                    />
                  </Field>
                  <Field label="Role">
                    <Select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                      <option value="member">member</option>
                      <option value="admin">admin</option>
                      <option value="viewer">viewer</option>
                    </Select>
                  </Field>
                </div>
                <p className="text-xs text-spine-muted">
                  Share the password securely. They can change it under Settings after logging in.
                </p>
                <Button type="submit">Add member</Button>
              </form>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="API keys" subtitle="Org-scoped keys for SDK and agent integrations." />
            <CardBody className="space-y-6">
              {createdKey ? (
                <Alert variant="warning">
                  <p className="font-medium">New key (shown once)</p>
                  <code className="mt-2 block break-all font-mono text-xs">{createdKey.raw_key}</code>
                </Alert>
              ) : null}

              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Status</th>
                      <th>Created</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {keys.map((k) => (
                      <tr key={k.id}>
                        <td>{k.name ?? "—"}</td>
                        <td>
                          <Badge variant={k.is_active ? "success" : "muted"}>
                            {k.is_active ? "active" : "revoked"}
                          </Badge>
                        </td>
                        <td className="text-xs text-spine-muted">
                          {new Date(k.created_at).toLocaleDateString()}
                        </td>
                        <td className="text-right">
                          {k.is_active ? (
                            <Button
                              type="button"
                              variant="ghost"
                              className="text-xs"
                              onClick={() => void revokeKey(k.id)}
                            >
                              Revoke
                            </Button>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <form onSubmit={(e) => void mintKey(e)} className="flex flex-wrap gap-3 items-end border-t border-spine-border pt-6">
                <Field label="Key name" className="min-w-[200px]">
                  <Input value={keyName} onChange={(e) => setKeyName(e.target.value)} />
                </Field>
                <Button type="submit">Mint API key</Button>
              </form>
            </CardBody>
          </Card>
        </>
      ) : (
        <Alert variant="info">
          Organization admins can manage team members and API keys here. Contact your admin for access.
        </Alert>
      )}
    </div>
  );
}
