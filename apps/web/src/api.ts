export type Check = { name: string; status: string; detail: string; fix?: string | null; latency_ms?: number };
export type Health = { version: string; status: string; checks: Check[] };
export type Policy = { allowed: boolean; risk: string; reasons: string[] };
export type StepView = {
  id: string; title: string; explain: string; command: string; expected: string;
  check: string | null; rollback: string | null; optional: boolean; long_running: boolean;
  declared_risk: string; policy: Policy; status: string; executed_command: string | null;
  modified: boolean; exit_code: number | null; started_at: string | null; finished_at: string | null;
};
export type Run = { id: string; runbook_id: string; title: string; status: string; created_at: string; steps: StepView[] };
export type RunbookSummary = { id: string; title: string; summary: string; category: string; steps: number };
export type Alert = { level: string; text: string };
type CallTotals = { calls: number; cost_usd: number; credits: number };
export type ModelCalls = {
  since: string | null; totals: { local: CallTotals; cloud: CallTotals };
  by_model: { model: string; provider: string; location: string; calls: number; prompt_tokens: number;
    completion_tokens: number; cost_usd: number; credits: number }[];
  by_day: { day: string; local_calls: number; cloud_calls: number; credits: number }[];
};

export type AuditRow = { id: number; at: string; actor: string; action: string; target: string; detail: any };
export type AuditFilter = { action?: string; actor?: string; q?: string; since?: string; until?: string; before?: number; limit?: number };
export type OllamaModel = {
  name: string; family: string | null; parameter_size: string | null; quantization: string | null; parent_model: string | null;
  size_gb: number; max_context: number | null; configured_context: number | null; capabilities: string[];
  loaded: boolean; loaded_gb: number | null; loaded_on_gpu_gb: number | null; used_by: string[];
};
export type ModelUsage = { calls?: number; prompt_tokens?: number; completion_tokens?: number; credits?: number; last_used?: string | null };
export type ModelCatalog = {
  local: { url: string; reachable: boolean; models: OllamaModel[] };
  remote: { url: string; reachable: boolean; models: OllamaModel[]; reason?: string };
  droid: { available: boolean; reason?: string; default?: string; models: (AgentModel & ModelUsage & { default: boolean })[] };
  routing: { task: string; route: string[]; note: string }[];
};
export type SettingRow = { name: string; env: string; description: string; value: any; default: any; is_default: boolean; secret: boolean };
export type SettingsView = { groups: { title: string; settings: SettingRow[] }[]; editable: boolean; how_to_change: string };
export type LogLine = { ts: string | null; level: string | null; msg: string; logger: string | null; extra: Record<string, any> };

function qs(params: Record<string, string | number | undefined>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}
export class ApiError extends Error {
  constructor(message: string, public status: number, public detail?: Policy | Record<string, unknown>) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "x-localpilot-client": "1" };
  if (body !== undefined) headers["content-type"] = "application/json";
  const r = await fetch(`/api/v1${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(data.error ?? data.detail ?? r.statusText, r.status, data.detail);
  return data as T;
}

const reads = new Map<string, Promise<unknown>>();
function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  if (method !== "GET") return request<T>(method, path, body);
  const existing = reads.get(path);
  if (existing) return existing as Promise<T>;
  const pending = request<T>(method, path).finally(() => reads.delete(path));
  reads.set(path, pending);
  return pending;
}

/** Health checks take seconds (they call CLIs), so concurrent callers share one request and a short cache. */
let healthCache: { at: number; p: Promise<Health> } | null = null;
function sharedHealth(force = false): Promise<Health> {
  if (force || !healthCache || Date.now() - healthCache.at > 10_000) {
    const p = req<Health>("GET", "/health");
    healthCache = { at: Date.now(), p };
    p.catch(() => { healthCache = null; });
  }
  return healthCache.p;
}

export const api = {
  health: sharedHealth,
  runbooks: () => req<RunbookSummary[]>("GET", "/runbooks"),
  runbook: (id: string) => req<{ runs: Run[] }>("GET", `/runbooks/${id}`),
  startRun: (id: string) => req<Run>("POST", `/runbooks/${id}/runs`),
  run: (id: string) => req<Run>("GET", `/runs/${id}`),
  evaluate: (run: string, step: string, command: string) =>
    req<Policy>("POST", `/runs/${run}/steps/${step}/evaluate`, { command }),
  execute: (run: string, step: string, command: string | null, confirmHighRisk: boolean) =>
    req<Run>("POST", `/runs/${run}/steps/${step}/execute`, { approved: true, command, confirm_high_risk: confirmHighRisk }),
  stop: (run: string, step: string) => req<Run>("POST", `/runs/${run}/steps/${step}/stop`),
  skip: (run: string, step: string) => req<Run>("POST", `/runs/${run}/steps/${step}/skip`),
  check: (run: string, step: string) =>
    req<{ passed: boolean; output: string }>("POST", `/runs/${run}/steps/${step}/check`, { approved: true }),
  output: (run: string, step: string) =>
    req<{ lines: string[]; next: number; done: boolean }>("GET", `/runs/${run}/steps/${step}/output`),
  usage: (includeRemote = true) =>
    req<Record<string, any> & { id: number; alerts: Alert[] }>("GET", `/usage${includeRemote ? "" : "?include_remote=false"}`),
  summary: (id: number) => req<{ source: string; model: string | null; text: string | null; error?: string;
    prompt_tokens?: number; completion_tokens?: number; duration_ms?: number }>("POST", `/usage/${id}/summary`),
  modelCalls: (since?: string) => req<ModelCalls>("GET", `/usage/model-calls${since ? `?since=${encodeURIComponent(since)}` : ""}`),
  audit: (limit = 200) => req<AuditRow[]>("GET", `/audit?limit=${limit}`),
  auditPage: (f: AuditFilter) => req<AuditRow[]>("GET", `/audit${qs(f)}`),
  auditActions: () => req<{ action: string; count: number }[]>("GET", "/audit/actions"),
  auditExportUrl: (format: "csv" | "json", f: AuditFilter) =>
    `/api/v1/audit/export${qs({ ...f, before: undefined, limit: undefined, format })}`,
  models: () => req<ModelCatalog>("GET", "/models"),
  settings: () => req<SettingsView>("GET", "/settings"),
  logs: (lines = 200) => req<{ path: string; lines: LogLine[] }>("GET", `/system/logs?lines=${lines}`),
};

export type AgentModel = { id: string; name: string; location: "local" | "cloud"; custom: boolean };
export type AgentRun = {
  id: string; session_id: string | null; parent_run_id: string | null; title: string; prompt: string; model: string;
  model_location: string; autonomy: string; cwd: string; status: string; state: string; result_text: string | null;
  error: string | null; usage: Record<string, number>; pending_approvals: number; created_at: string; finished_at: string | null;
};
export type AgentEvent = { seq: number; at: string; type: string; data: Record<string, any> };
export type Approval = {
  id: string; source: string; run_id: string | null; kind: string; title: string; risk: string;
  details: { actions?: Record<string, any>[] }; options: string[]; status: string; decided_by: string | null;
  comment: string | null; created_at: string; decided_at: string | null;
};

export const agents = {
  models: (refresh = false) =>
    req<{ default: string; models: AgentModel[]; workspaces: string[] }>("GET", `/agents/models${refresh ? "?refresh=true" : ""}`),
  runs: () => req<AgentRun[]>("GET", "/agents/runs"),
  run: (id: string) => req<AgentRun>("GET", `/agents/runs/${id}`),
  events: (id: string, after = 0) =>
    req<{ events: AgentEvent[]; next: number; partial: string; active: boolean }>("GET", `/agents/runs/${id}/events?after=${after}`),
  start: (body: { prompt: string; model: string; autonomy: string; cwd: string; continue_run_id?: string }) =>
    req<AgentRun>("POST", "/agents/runs", body),
  stop: (id: string) => req<AgentRun>("POST", `/agents/runs/${id}/stop`),
  approvals: (status?: string) => req<Approval[]>("GET", `/approvals${status ? `?status=${status}` : ""}`),
  decide: (id: string, decision: "approve" | "deny", comment?: string) =>
    req<Approval>("POST", `/approvals/${id}/decide`, { decision, comment: comment || null }),
};
