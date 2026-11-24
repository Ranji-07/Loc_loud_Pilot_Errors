function qs(params: Record<string, string | number | undefined>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}
import type * as T from "../../shared-types/src/index";
export * from "../../shared-types/src/index";

export function loopbackUrl(value: string): string {
  const url = new URL(value);
  if (!["http:", "https:"].includes(url.protocol) || !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname) ||
      url.username || url.password || url.search || url.hash || (url.pathname !== "/" && url.pathname !== "")) {
    throw new Error("LocalPilot server URL must be an HTTP(S) loopback origin without credentials");
  }
  return url.origin;
}

export class ApiError extends Error {
  constructor(message: string, public status: number, public detail?: T.Policy | Record<string, unknown>) {
    super(message);
  }
}

export type ApiFn = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
type Options = { baseUrl?: string | (() => string); surface?: "dashboard" | "vscode"; fetch?: typeof fetch };
export function createClient(options: Options = {}) {
  const base = () => {
    const value = typeof options.baseUrl === "function" ? options.baseUrl() : options.baseUrl || "";
    return value ? loopbackUrl(value) : "";
  };
  const url = (path: string) => `${base()}/api/v1${path}`;
  const send = options.fetch || globalThis.fetch.bind(globalThis);
  const headers = { "x-localpilot-client": "1", "x-localpilot-surface": options.surface || "dashboard" };
  async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const r = await send(url(path), { method, headers: { ...headers, ...(body !== undefined ? { "content-type": "application/json" } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(method === "GET" ? 30000 : 120000) });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      const detail = data.error ?? data.detail;
      const message = typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map(x => x.msg).join("; ") : r.statusText;
      throw new ApiError(message || `HTTP ${r.status}`, r.status, data.detail);
    }
    return data as T;
  }
  const reads = new Map<string, Promise<unknown>>();
  function req<T>(method: string, path: string, body?: unknown): Promise<T> {
    if (method !== "GET") return request<T>(method, path, body);
    const key = url(path);
    const existing = reads.get(key);
    if (existing) return existing as Promise<T>;
    const pending = request<T>(method, path).finally(() => reads.delete(key));
    reads.set(key, pending);
    return pending;
  }
  let healthCache: { key: string; at: number; p: Promise<T.Health> } | null = null;
  function sharedHealth(force = false): Promise<T.Health> {
    const key = base();
    if (force || !healthCache || key !== healthCache.key || Date.now() - healthCache.at > 10000) {
      const p = req<T.Health>("GET", "/health");
      healthCache = { key, at: Date.now(), p };
      p.catch(() => { if (healthCache?.p === p) healthCache = null; });
    }
    return healthCache.p;
  }
const api = {
  health: sharedHealth,
  runbooks: () => req<T.RunbookSummary[]>("GET", "/runbooks"),
  runbook: (id: string) => req<{ runs: T.Run[] }>("GET", `/runbooks/${id}`),
  startRun: (id: string) => req<T.Run>("POST", `/runbooks/${id}/runs`),
  run: (id: string) => req<T.Run>("GET", `/runs/${id}`),
  evaluate: (run: string, step: string, command: string) =>
    req<T.Policy>("POST", `/runs/${run}/steps/${step}/evaluate`, { command }),
  execute: (run: string, step: string, command: string | null, confirmHighRisk: boolean) =>
    req<T.Run>("POST", `/runs/${run}/steps/${step}/execute`, { approved: true, command, confirm_high_risk: confirmHighRisk }),
  stop: (run: string, step: string) => req<T.Run>("POST", `/runs/${run}/steps/${step}/stop`),
  skip: (run: string, step: string) => req<T.Run>("POST", `/runs/${run}/steps/${step}/skip`),
  check: (run: string, step: string) =>
    req<{ passed: boolean; output: string }>("POST", `/runs/${run}/steps/${step}/check`, { approved: true }),
  output: (run: string, step: string) =>
    req<{ lines: string[]; next: number; done: boolean }>("GET", `/runs/${run}/steps/${step}/output`),
  usage: (includeRemote = true) =>
    req<Record<string, any> & { id: number; alerts: T.Alert[] }>("GET", `/usage${includeRemote ? "" : "?include_remote=false"}`),
  summary: (id: number) => req<{ source: string; model: string | null; text: string | null; error?: string;
    prompt_tokens?: number; completion_tokens?: number; duration_ms?: number }>("POST", `/usage/${id}/summary`),
  modelCalls: (since?: string) => req<T.ModelCalls>("GET", `/usage/model-calls${since ? `?since=${encodeURIComponent(since)}` : ""}`),
  audit: (limit = 200) => req<T.AuditRow[]>("GET", `/audit?limit=${limit}`),
  auditPage: (f: T.AuditFilter) => req<T.AuditRow[]>("GET", `/audit${qs(f)}`),
  auditActions: () => req<{ action: string; count: number }[]>("GET", "/audit/actions"),
  auditExportUrl: (format: "csv" | "json", f: T.AuditFilter) =>
    url(`/audit/export${qs({ ...f, before: undefined, limit: undefined, format })}`),
  models: () => req<T.ModelCatalog>("GET", "/models"),
  settings: () => req<T.SettingsView>("GET", "/settings"),
  logs: (lines = 200) => req<{ path: string; lines: T.LogLine[] }>("GET", `/system/logs?lines=${lines}`),
};

const agents = {
  models: (refresh = false) =>
    req<{ default: string; models: T.AgentModel[]; workspaces: string[] }>("GET", `/agents/models${refresh ? "?refresh=true" : ""}`),
  runs: () => req<T.AgentRun[]>("GET", "/agents/runs"),
  run: (id: string) => req<T.AgentRun>("GET", `/agents/runs/${id}`),
  events: (id: string, after = 0) =>
    req<{ events: T.AgentEvent[]; next: number; partial: string; active: boolean }>("GET", `/agents/runs/${id}/events?after=${after}`),
  start: (body: { prompt: string; model: string; autonomy: string; cwd: string; continue_run_id?: string }) =>
    req<T.AgentRun>("POST", "/agents/runs", body),
  stop: (id: string) => req<T.AgentRun>("POST", `/agents/runs/${id}/stop`),
  approvals: (status?: string) => req<T.Approval[]>("GET", `/approvals${status ? `?status=${status}` : ""}`),
  checkpoints: (id: string) => req<T.Checkpoint[]>("GET", `/agents/runs/${id}/checkpoints`),
  rollback: (id: string) => req<{ id: string; status: string }>("POST", `/checkpoints/${id}/rollback`, { approved: true }),
  decide: (id: string, decision: "approve" | "deny", comment?: string) =>
    req<T.Approval>("POST", `/approvals/${id}/decide`, { decision, comment: comment || null }),
};
  const workspace = {
    projects: (before?: string) => req<T.Project[]>("GET", `/projects${qs({ before })}`),
    project: (id: string) => req<T.Project>("GET", `/projects/${id}`),
    createProject: (name: string, root: string) => req<T.Project>("POST", "/projects", { name, root }),
    saveProject: (p: T.Project) => req<T.Project>("PATCH", `/projects/${p.id}`, {
      name: p.name, instructions: p.instructions, architecture: p.architecture, revision: p.revision }),
    context: (id: string, before?: string) => req<T.ContextItem[]>("GET", `/projects/${id}/context${qs({ before })}`),
    saveContext: (project: string, item: { kind: T.ContextItem["kind"]; title: string; content?: string; path?: string | null; id?: string; revision?: number }) =>
      req<T.ContextItem>(item.id ? "PUT" : "POST", `/projects/${project}/context${item.id ? `/${item.id}` : ""}`,
        { kind: item.kind, title: item.title, content: item.content || "", path: item.path, revision: item.revision || 1 }),
    profiles: (before?: string) => req<T.AgentProfile[]>("GET", `/agent-profiles${qs({ before })}`),
    saveProfile: (p: Omit<T.AgentProfile, "id" | "adapter" | "revision"> & { id?: string; revision?: number }) =>
      req<T.AgentProfile>(p.id ? "PATCH" : "POST", `/agent-profiles${p.id ? `/${p.id}` : ""}`, {
        name: p.name, role: p.role, instructions: p.instructions, model: p.model, enabled: p.enabled, revision: p.revision || 1 }),
    prompts: (id: string, before?: string) => req<T.SavedPrompt[]>("GET", `/projects/${id}/prompts${qs({ before })}`),
    savePrompt: (project: string, name: string, content: string, id?: string, revision = 1) =>
      req<T.SavedPrompt>(id ? "PUT" : "POST", `/projects/${project}/prompts${id ? `/${id}` : ""}`, { name, content, revision }),
    versions: (id: string, before?: number) => req<T.PromptVersion[]>("GET", `/prompts/${id}/versions${qs({ before })}`),
    tasks: (project_id?: string, before?: string) => req<T.Task[]>("GET", `/tasks${qs({ project_id, before })}`),
    task: (id: string) => req<T.Task>("GET", `/tasks/${id}`),
    createTask: (body: T.TaskInput) => req<T.Task>("POST", "/tasks", body),
    saveTask: (id: string, body: T.TaskInput & { revision: number }) => req<T.Task>("PATCH", `/tasks/${id}`, body),
    preview: (id: string) => req<T.TaskPreview>("GET", `/tasks/${id}/preview`),
    start: (id: string, revision: number, preview_hash: string, allow_cloud: boolean) =>
      req<T.Task>("POST", `/tasks/${id}/start`, { revision, preview_hash, approved: true, allow_cloud }),
    cancel: (id: string) => req<T.Task>("POST", `/tasks/${id}/cancel`),
  };
  async function* streamRun(id: string, after: number, signal: AbortSignal): AsyncGenerator<T.RunChunk> {
    const r = await send(url(`/agents/runs/${id}/stream?after=${after}`), { headers, signal });
    if (!r.ok || !r.body) throw new ApiError(`Stream failed (HTTP ${r.status})`, r.status);
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) return;
        buffer += decoder.decode(value, { stream: true });
        let boundary: RegExpExecArray | null;
        while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
          const packet = buffer.slice(0, boundary.index);
          buffer = buffer.slice(boundary.index + boundary[0].length);
          const lines = packet.split(/\r?\n/);
          const data = lines.filter(l => l.startsWith("data:")).map(l => l.slice(5).trimStart()).join("\n");
          if (!data) continue;
          const parsed = JSON.parse(data);
          if (lines.includes("event: end")) {
            yield { events: [], next: parsed.next, partial: "", active: false, run: parsed.run };
            return;
          }
          yield parsed as T.RunChunk;
        }
      }
    } finally {
      await reader.cancel().catch(() => {});
      reader.releaseLock();
    }
  }
  const call: ApiFn = (path, method = "GET", body) => req(method, path, body);
  return { api, agents, workspace, call, url, streamRun };
}
