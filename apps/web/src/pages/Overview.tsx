import { useCallback, useEffect, useState } from "react";
import { ArrowRight, Bot, Cpu, Plus, Server, Wallet } from "lucide-react";
import { agents, api, type AgentModel, type AgentRun, type Approval, type AuditRow, type Health, type ModelCalls } from "../api";
import { ago, monthStart } from "../fmt";
import { go } from "../nav";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from "../ui";

const ACTIVE = ["starting", "running", "waiting_approval"];
type Usage = Awaited<ReturnType<typeof api.usage>>;


function usePoll<T>(fn: () => Promise<T>, ms: number | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => fn().then((d) => { setData(d); setError(null); }).catch((e) => setError((e as Error).message)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []);
  useEffect(() => {
    load();
    if (ms === null) return;
    const t = setInterval(load, ms);
    return () => clearInterval(t);
  }, [load, ms]);
  return { data, error, reload: load };
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-3 py-1.5 text-sm">
      <span className="w-28 shrink-0 text-muted">{label}</span>
      <span className="min-w-0 flex-1 [overflow-wrap:anywhere]">{children}</span>
    </div>
  );
}

export default function Overview() {
  const health = usePoll<Health>(() => api.health(), 30000);
  const pending = usePoll<Approval[]>(() => agents.approvals("pending"), 5000);
  const runs = usePoll<AgentRun[]>(agents.runs, 5000);
  const models = usePoll<{ default: string; models: AgentModel[] }>(() => agents.models(), null);
  const calls = usePoll<ModelCalls>(() => api.modelCalls(monthStart()), 30000);
  const usage = usePoll<Usage>(() => api.usage(false), null);
  const activity = usePoll<AuditRow[]>(() => api.audit(8), 15000);

  const issues = health.data?.checks.filter((c) => c.status === "warn" || c.status === "error") ?? [];
  const check = (n: string) => health.data?.checks.find((c) => c.name === n);
  const active = runs.data?.filter((r) => ACTIVE.includes(r.status)) ?? [];
  const defaultModel = models.data?.models.find((m) => m.id === models.data?.default);
  const localModels = models.data?.models.filter((m) => m.location === "local") ?? [];
  const aws = usage.data?.aws as { available?: boolean; reason?: string; instances?: { state: string; cost_since_start_usd: number | null }[] } | undefined;
  const awsRunning = aws?.instances?.filter((i) => i.state === "running") ?? [];
  const awsCost = awsRunning.reduce((s, i) => s + (i.cost_since_start_usd ?? 0), 0);
  const local = usage.data?.local as { cpu_percent?: number; ram_used_percent?: number } | undefined;

  return (
    <div className="space-y-4">
      <PageHeader title="Overview" description="What needs you now, and the state of agents, models, compute and spend."
                  actions={<button className="btn-primary" onClick={() => go("agents")}><Plus aria-hidden className="h-4 w-4" />New Droid task</button>} />

      <ErrorState error={health.error && `Cannot reach the LocalPilot backend: ${health.error}`} onRetry={health.reload} />

      <Card title="Needs your attention">
        {!pending.data || !health.data ? <LoadingState /> : pending.data.length === 0 && issues.length === 0 ? (
          <div className="flex items-center gap-2 text-sm"><StatusBadge value="ok" label="All clear" />No pending approvals and all health checks pass.</div>
        ) : (
          <ul className="divide-y divide-border">
            {pending.data.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                <StatusBadge value="pending" label="Approval" />
                <span className="min-w-0 flex-1 truncate">{a.title}</span>
                <StatusBadge value={a.risk} label={`${a.risk} risk`} />
                <button className="btn-ghost py-0.5" onClick={() => go("decisions/approvals")}>Review<ArrowRight aria-hidden className="h-3.5 w-3.5" /></button>
              </li>
            ))}
            {issues.map((c) => (
              <li key={c.name} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                <StatusBadge value={c.status} label={c.status === "error" ? "Error" : "Warning"} />
                <span className="font-medium">{c.name.replaceAll("_", " ")}</span>
                <span className="min-w-0 flex-1 text-muted">{c.fix ?? c.detail}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Agents" actions={<a className="text-xs text-muted underline hover:text-text" href="#/agents">All runs</a>}>
          {runs.error ? <ErrorState error={runs.error} onRetry={runs.reload} /> : !runs.data ? <LoadingState /> : runs.data.length === 0 ? (
            <EmptyState title="No agent runs yet" action={<button className="btn-ghost" onClick={() => go("agents")}><Bot aria-hidden className="h-4 w-4" />Start a Droid task</button>} />
          ) : (
            <>
              <p className="mb-2 text-sm">{active.length ? `${active.length} running` : "Nothing running"} · {runs.data.length} run{runs.data.length > 1 ? "s" : ""} recorded</p>
              <ul className="divide-y divide-border">
                {runs.data.slice(0, 5).map((r) => (
                  <li key={r.id} className="flex items-center gap-2 py-1.5 text-sm">
                    <StatusBadge value={r.status} />
                    <a className="min-w-0 flex-1 truncate hover:underline" href={`#/agents/runs/${r.id}`}>{r.title}</a>
                    <span className="shrink-0 text-xs text-muted">{r.model_location} · {ago(r.created_at)}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>

        <Card title="Models" actions={<Cpu aria-hidden className="h-4 w-4 text-muted" />}>
          {models.error ? <ErrorState error={`Droid models: ${models.error}`} onRetry={models.reload} /> : !models.data ? <LoadingState /> : (
            <div className="divide-y divide-border">
              <Row label="Droid default">{defaultModel?.name ?? models.data.default} <StatusBadge value="x" tone="neutral" label={defaultModel?.location === "local" ? "local" : "cloud, uses credits"} /></Row>
              <Row label="Local models">{localModels.length ? localModels.map((m) => m.name).join(", ") : "None registered"}</Row>
              <Row label="Ollama">{check("ollama") ? <><StatusBadge value={check("ollama")!.status} /> <span className="text-muted">{check("ollama")!.detail}</span></> : "…"}</Row>
            </div>
          )}
        </Card>

        <Card title="Compute" actions={<Server aria-hidden className="h-4 w-4 text-muted" />}>
          <div className="divide-y divide-border">
            <Row label="This machine">{local ? `CPU ${local.cpu_percent}% · RAM ${local.ram_used_percent}% used` : usage.error ? "Unavailable" : "Measuring…"}</Row>
            <Row label="Local GPU">{check("local_gpu")?.detail ?? "…"}</Row>
            <Row label="Remote GPU">{check("remote_ollama") ? <><StatusBadge value={check("remote_ollama")!.status} /> <span className="text-muted">{check("remote_ollama")!.detail}</span></> : "…"}</Row>
            <Row label="AWS">{!usage.data ? (usage.error ? "Unavailable" : "Checking…") : !aws?.available ? (aws?.reason ?? "Not checked") : awsRunning.length ? `${awsRunning.length} instance(s) running` : "No LocalPilot instances running in this region. Other charges are not checked."}</Row>
          </div>
        </Card>

        <Card title="Spend this month" actions={<Wallet aria-hidden className="h-4 w-4 text-muted" />}>
          {calls.error ? <ErrorState error={calls.error} onRetry={calls.reload} /> : !calls.data ? <LoadingState /> : (
            <div className="divide-y divide-border">
              <Row label="Factory cloud">{calls.data.totals.cloud.credits.toLocaleString()} credits · {calls.data.totals.cloud.calls} run(s)</Row>
              <Row label="Local models">{calls.data.totals.local.calls} call(s) · no charge</Row>
              <Row label="AWS GPU">{!usage.data || !aws?.available ? "Estimate unavailable until the AWS check succeeds" : awsRunning.length ? `≈ $${awsCost.toFixed(2)} since the running instance(s) started (estimate from config/pricing.yaml)` : "No running instance compute estimated. Storage and other charges are not included."}</Row>
            </div>
          )}
        </Card>
      </div>

      <Card title="Recent activity" actions={<a className="text-xs text-muted underline hover:text-text" href="#/history">History</a>}>
        {activity.error ? <ErrorState error={activity.error} onRetry={activity.reload} /> : !activity.data ? <LoadingState /> : activity.data.length === 0 ? (
          <EmptyState title="No activity yet" />
        ) : (
          <ul className="divide-y divide-border">
            {activity.data.map((e) => (
              <li key={e.id} className="flex items-center gap-3 py-1.5 text-sm">
                <span className="w-24 shrink-0 text-xs text-muted">{ago(e.at)}</span>
                <span className="font-mono text-xs">{e.action}</span>
                <span className="min-w-0 flex-1 truncate text-xs text-muted">{e.actor}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
