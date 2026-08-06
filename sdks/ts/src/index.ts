export type InterceptResponse = {
  allowed: boolean;
  decision: string;
  reason: string;
  audit_event_id: string;
  request_id: string;
  approval_id?: string | null;
};

export type SpineClientOptions = {
  baseUrl: string;
  orgKey: string;
  fetchFn?: typeof fetch;
};

export class SpineClient {
  private readonly baseUrl: string;
  private readonly orgKey: string;
  private readonly fetchFn: typeof fetch;

  constructor(opts: SpineClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, "");
    this.orgKey = opts.orgKey;
    this.fetchFn = opts.fetchFn ?? fetch;
  }

  private headers(requestId?: string): Record<string, string> {
    const h: Record<string, string> = { "X-Org-Key": this.orgKey, "content-type": "application/json" };
    if (requestId) h["X-Request-ID"] = requestId;
    return h;
  }

  async intercept(input: {
    agentId: string;
    actionType: string;
    targetResource?: string | null;
    metadata?: Record<string, unknown> | null;
    traceId?: string;
    spanId?: string;
    requestId?: string;
  }): Promise<InterceptResponse> {
    const correlation: Record<string, string> = {};
    if (input.traceId) correlation.trace_id = input.traceId;
    if (input.spanId) correlation.span_id = input.spanId;
    if (input.requestId) correlation.request_id = input.requestId;

    const body: Record<string, unknown> = {
      agent_id: input.agentId,
      action: {
        action_type: input.actionType,
        target_resource: input.targetResource ?? null,
        metadata: input.metadata ?? null,
      },
    };
    if (Object.keys(correlation).length) body.correlation = correlation;

    const res = await this.fetchFn(`${this.baseUrl}/v1/intercept`, {
      method: "POST",
      headers: this.headers(input.requestId),
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Spine intercept failed: HTTP ${res.status} ${text}`);
    }
    return (await res.json()) as InterceptResponse;
  }
}
