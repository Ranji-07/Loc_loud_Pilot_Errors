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
export type CallTotals = { calls: number; cost_usd: number; credits: number };
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

export type AgentModel = { id: string; name: string; location: "local" | "cloud"; custom: boolean };
export type AgentRun = {
  id: string; session_id: string | null; parent_run_id: string | null; title: string; prompt: string; model: string;
  model_location: string; autonomy: string; cwd: string; status: string; state: string; result_text: string | null;
  error: string | null; usage: Record<string, number>; pending_approvals: number; created_at: string; finished_at: string | null;
};
export type AgentEvent = { seq: number; at: string; type: string; data: Record<string, any> };
export type Approval = {
  id: string; source: string; run_id: string | null; kind: string; title: string; risk: string;
  details: { actions?: Record<string, any>[]; checkpoint_id?: string; checkpoint_error?: string }; options: string[]; status: string; decided_by: string | null;
  comment: string | null; created_at: string; decided_at: string | null;
};

export type Project = { id: string; name: string; root: string; instructions: string; architecture: string; revision: number; created_at: string };
export type ContextItem = { id: string; project_id: string; kind: "file" | "instructions" | "architecture" | "decision" | "note";
  title: string; content: string; path: string | null; source_hash: string; source_commit: string | null; revision: number; created_at: string };
export type AgentProfile = { id: string; name: string; role: string; adapter: string; instructions: string;
  model: string | null; enabled: boolean; revision: number };
export type SavedPrompt = { id: string; project_id: string; name: string; revision: number; created_at: string };
export type PromptVersion = { id: number; prompt_id: string; version: number; content: string; created_at: string };
export type TaskInput = { project_id: string; agent_id: string; objective: string; requirements?: string; acceptance?: string;
  model?: string | null; context_ids?: string[]; include_instructions?: boolean; include_architecture?: boolean;
  prompt_id?: string | null; variables?: Record<string, string>; continue_run_id?: string | null };
export type TaskPreview = { prompt: string; model: string; location: string; cwd: string; sources: Partial<ContextItem>[];
  project_revision: number; agent_revision: number; task_revision: number; estimated_prompt_tokens: number; estimate_note: string; preview_hash: string };
export type Task = TaskInput & { id: string; status: string; run_id: string | null; error: string | null; revision: number;
  created_at: string; queued_at: string | null; allow_cloud: boolean; snapshot?: TaskPreview;
  run?: AgentRun; attempts?: { id: number; run_id: string; snapshot: TaskPreview; created_at: string }[]; attempt_count?: number };
export type Checkpoint = { id: string; approval_id: string; status: string; files: { path: string; changed: boolean }[] };
export type RunChunk = { events: AgentEvent[]; next: number; partial: string; active: boolean; run?: AgentRun };
