export type Check = { name: string; status: string; detail: string; hint?: string | null };
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

export class ApiError extends Error {
  constructor(message: string, public status: number, public detail?: Policy | Record<string, unknown>) {
    super(message);
  }
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "x-localpilot-client": "1" };
  if (body !== undefined) headers["content-type"] = "application/json";
  const r = await fetch(`/api/v1${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(data.error ?? data.detail ?? r.statusText, r.status, data.detail);
  return data as T;
}

export const api = {
  health: () => req<Health>("GET", "/health"),
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
  usage: () => req<Record<string, any> & { id: number; alerts: Alert[] }>("GET", "/usage"),
  summary: (id: number) => req<{ source: string; model: string | null; text: string | null; error?: string;
    prompt_tokens?: number; completion_tokens?: number; duration_ms?: number }>("POST", `/usage/${id}/summary`),
  modelCalls: () => req<{ by_model: { model: string; provider: string; calls: number; prompt_tokens: number;
    completion_tokens: number; cost_usd: number }[] }>("GET", "/usage/model-calls"),
  audit: () => req<{ id: number; at: string; actor: string; action: string; target: string; detail: any }[]>("GET", "/audit?limit=200"),
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
