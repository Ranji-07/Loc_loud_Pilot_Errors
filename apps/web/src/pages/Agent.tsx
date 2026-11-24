import { useEffect, useMemo, useRef, useState } from "react";
import { RotateCcw, Square } from "lucide-react";
import { agents, api, type AgentEvent, type AgentModel, type AgentRun, type Approval, type SettingsView } from "../api";
import { duration, num, runtime } from "../fmt";
import { go } from "../nav";
import { Badge, Card, EmptyState, ErrorBox, LoadingState, PageHeader, StatusBadge, Tabs } from "../ui";

export const ACTIVE = ["starting", "running", "waiting_approval"];

export function tokens(run: AgentRun) {
  const u = run.usage ?? {};
  return (u.input_tokens ?? 0) + (u.output_tokens ?? 0) + (u.cache_read_tokens ?? 0) + (u.cache_creation_tokens ?? 0);
}

function credits(run: AgentRun) {
  const c = run.usage?.factory_credits;
  return c ? `${c.toLocaleString()} Factory credits` : run.model_location === "local" ? "local model, no credits" : "";
}

export function ApprovalCard({ a, onDone }: { a: Approval; onDone: () => void }) {
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const decide = async (d: "approve" | "deny") => {
    setBusy(true); setError(null);
    try { await agents.decide(a.id, d, comment); onDone(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className="card space-y-2 border-warning">
      <div className="flex items-center gap-2">
        <Badge value={a.risk} label={`${a.risk} risk`} />
        <span className="font-medium">{a.title}</span>
      </div>
      {(a.details.actions ?? []).map((act, i) => (
        <div key={i} className="space-y-1 text-xs">
          {act.file_path && <div className="font-mono text-text">{act.file_path}</div>}
          {act.full_command && <pre className="whitespace-pre-wrap rounded bg-bg p-2 font-mono">{act.full_command}</pre>}
          {act.risk_level_reason && <div className="text-muted">{act.risk_level_reason}</div>}
          {(act.content ?? act.new_content ?? act.patch_content) && (
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded bg-bg p-2 font-mono">
              {act.content ?? act.patch_content ?? act.new_content}
            </pre>
          )}
        </div>
      ))}
      <input className="field w-full" aria-label="Note to Droid"
             placeholder="Optional note to Droid (sent with a deny)" value={comment} onChange={(e) => setComment(e.target.value)} />
      <div className="flex gap-2">
        <button className="btn-primary" disabled={busy} onClick={() => decide("approve")}>Approve once</button>
        <button className="btn-danger" disabled={busy} onClick={() => decide("deny")}>Deny</button>
      </div>
      <ErrorBox error={error} />
    </div>
  );
}

function EventLine({ e }: { e: AgentEvent }) {
  const d = e.data;
  switch (e.type) {
    case "assistant":
      return <div className="whitespace-pre-wrap text-sm">{d.text}</div>;
    case "tool_call":
      return <div className="font-mono text-xs text-muted">→ {d.tool} {typeof d.input === "string" ? d.input.slice(0, 300) : ""}</div>;
    case "tool_result":
      return <div className="max-h-40 overflow-auto whitespace-pre-wrap font-mono text-xs text-muted">
        ← {d.tool}{d.is_error ? " (error)" : ""}: {String(d.content).slice(0, 1500)}</div>;
    case "approval_requested":
      return <div className="text-xs text-text">Permission requested: {d.title}</div>;
    case "approval_decided":
      return <div className="text-xs text-text">Decision: {d.decision}</div>;
    case "error":
      return <div className="text-xs text-text"><StatusBadge value="error" /> {d.message}</div>;
    case "finished":
      return <div className="text-xs text-muted">Run finished: {d.status}{d.error ? ` (${d.error})` : ""}</div>;
    default:
      return <div className="text-xs text-muted">{e.type}</div>;
  }
}

/** Grouped model picker shared by the Agents page and Prompt Studio. */
export function ModelSelect({ models, value, onChange, id }: { models: AgentModel[]; value: string; onChange: (v: string) => void; id?: string }) {
  const local = models.filter((m) => m.location === "local");
  const cloud = models.filter((m) => m.location === "cloud");
  const chosen = models.find((m) => m.id === value);
  return (
    <>
      <select id={id} className="field w-full" value={value} onChange={(e) => onChange(e.target.value)}>
        {local.length > 0 && <optgroup label="Local (Ollama, no credits)">
          {local.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</optgroup>}
        <optgroup label="Factory cloud (uses Factory credits)">
          {cloud.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</optgroup>
      </select>
      <div className="text-xs text-muted">
        {chosen?.location === "local" ? "Runs on this machine through Ollama. Slow on CPU." : "Sent to Factory; usage is billed in Factory credits."}
      </div>
    </>
  );
}

export const AUTONOMY = [
  { id: "off", label: "Off: ask before every change or command (recommended)" },
  { id: "low", label: "Low: Droid may make low-risk file edits without asking" },
];

function RunsTab({ selected, runs, pending, models, workspaces, defaultModel, refreshLists }: {
  selected: string | null; runs: AgentRun[] | null; pending: Approval[]; models: AgentModel[]; workspaces: string[];
  defaultModel: string; refreshLists: () => void;
}) {
  const [model, setModel] = useState("");
  const [autonomy, setAutonomy] = useState("off");
  const [cwd, setCwd] = useState("");
  const [prompt, setPrompt] = useState("");
  const [run, setRun] = useState<AgentRun | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [partial, setPartial] = useState("");
  const [followUp, setFollowUp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (!model && defaultModel) setModel(defaultModel); }, [defaultModel, model]);
  useEffect(() => { if (!cwd && workspaces[0]) setCwd(workspaces[0]); }, [workspaces, cwd]);

  useEffect(() => {
    let disposed = false;
    setRun(null); setError(null);
    if (!selected) return;
    setEvents([]); setPartial("");
    agents.run(selected).then((r) => { if (!disposed) setRun(r); }).catch((e) => { if (!disposed) setError((e as Error).message); });
    const es = new EventSource(`/api/v1/agents/runs/${selected}/stream`);
    es.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.events?.length) setEvents((prev) => [...prev, ...d.events.filter((x: AgentEvent) => !prev.some((p) => p.seq === x.seq))]);
      setPartial(d.partial ?? "");
      if (d.run) setRun(d.run);
      refreshLists();
    };
    es.addEventListener("end", (m) => {
      const d = JSON.parse((m as MessageEvent).data);
      if (d.run) setRun(d.run);
      setPartial(""); refreshLists(); es.close();
    });
    es.onerror = () => { if (!disposed) setError("Run stream disconnected. Reopen the run to reconnect."); es.close(); };
    return () => { disposed = true; es.close(); };
  }, [selected, refreshLists]);

  useEffect(() => { endRef.current?.scrollIntoView({ block: "nearest" }); }, [events.length, partial]);

  const start = async (body: { prompt: string; model: string; autonomy: string; cwd: string; continue_run_id?: string }) => {
    setBusy(true); setError(null);
    try {
      const r = await agents.start(body);
      setPrompt(""); setFollowUp(""); refreshLists(); go(`agents/runs/${r.id}`);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const runPending = pending.filter((a) => a.run_id === selected);
  const otherPending = pending.filter((a) => a.run_id !== selected);

  return (
    <div className="space-y-4">
      <ErrorBox error={error} />
      <div className="card space-y-3">
        <label htmlFor="agent-task" className="sr-only">Task</label>
        <textarea id="agent-task" className="field h-24 w-full p-2"
                  placeholder="Describe the task, e.g. 'Explain what backend/localpilot/policy.py blocks'"
                  value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
          <div className="space-y-1">
            <label htmlFor="agent-model" className="text-muted">Model</label>
            <ModelSelect id="agent-model" models={models} value={model} onChange={setModel} />
          </div>
          <label className="space-y-1">
            <div className="text-muted">Autonomy</div>
            <select className="field w-full" value={autonomy} onChange={(e) => setAutonomy(e.target.value)}>
              {AUTONOMY.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
            </select>
          </label>
          <label className="space-y-1">
            <div className="text-muted">Folder</div>
            <select className="field w-full" value={cwd} onChange={(e) => setCwd(e.target.value)}>
              {workspaces.map((w) => <option key={w} value={w}>{w}</option>)}
            </select>
          </label>
        </div>
        <p className="text-xs text-muted">Prompt estimate: roughly {num(Math.ceil(prompt.length / 4))} tokens (4 characters per token). Droid instructions, file context and output add more.
          {models.find((m) => m.id === model)?.location === "local" ? " No Factory credits for local inference." : " Factory credits apply; a reliable cost quote is not available."}
        </p>
        <button className="btn-primary" disabled={busy || !prompt.trim() || !model} onClick={() => start({ prompt, model, autonomy, cwd })}>Start Droid</button>
      </div>

      {otherPending.length > 0 && (
        <div className="card border-warning text-sm">
          {otherPending.length} approval(s) waiting on other runs:{" "}
          {otherPending.map((a) => <a key={a.id} className="mr-2 underline" href={`#/agents/runs/${a.run_id}`}>{a.title}</a>)}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card max-h-[70vh] space-y-1 overflow-auto">
          <h2 className="mb-2 text-sm font-semibold">Runs</h2>
          {!runs ? <LoadingState /> : runs.length === 0 && <div className="text-sm text-muted">No runs yet.</div>}
          {runs?.map((r) => (
            <a key={r.id} href={`#/agents/runs/${r.id}`} aria-current={selected === r.id ? "true" : undefined}
               className={`block w-full rounded px-2 py-1.5 text-left text-sm ${selected === r.id ? "bg-surface-2" : "hover:bg-surface-2"}`}>
              <div className="flex items-center gap-2"><Badge value={r.status} /><span className="truncate">{r.title}</span></div>
              <div className="text-xs text-muted">
                {new Date(r.created_at).toLocaleString()} · {r.model_location} · {runtime(r.created_at, r.finished_at)}
                {tokens(r) > 0 && ` · ${num(tokens(r))} tokens`}
              </div>
            </a>
          ))}
        </div>

        <div className="space-y-3 lg:col-span-2">
          {!run && !error && <div className="card text-sm text-muted">{selected ? <LoadingState /> : "Start a task or pick a run."}</div>}
          {run && (
            <>
              <div className="card space-y-1 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge value={run.status} /><span className="font-medium">{run.title}</span>
                  <span className="ml-auto flex gap-2">
                    {ACTIVE.includes(run.status) ? (
                      <button className="btn-danger" onClick={() => agents.stop(run.id).then(setRun).catch((e) => setError((e as Error).message))}>
                        <Square aria-hidden className="h-3.5 w-3.5" />Stop</button>
                    ) : (
                      <button className="btn-ghost" disabled={busy} title="Start a new run with the same task, model, autonomy and folder"
                              onClick={() => start({ prompt: run.prompt, model: run.model, autonomy: run.autonomy, cwd: run.cwd })}>
                        <RotateCcw aria-hidden className="h-3.5 w-3.5" />Retry</button>
                    )}
                  </span>
                </div>
                <div className="text-xs text-muted">
                  {run.model} ({run.model_location}) · autonomy {run.autonomy} · {run.cwd} · {runtime(run.created_at, run.finished_at)}
                  {credits(run) && ` · ${credits(run)}`}
                </div>
                {run.error && <div className="text-xs text-text"><StatusBadge value="error" label="Error" /> {run.error}</div>}
              </div>
              {runPending.map((a) => <ApprovalCard key={a.id} a={a} onDone={refreshLists} />)}
              <div className="card max-h-[55vh] space-y-2 overflow-auto">
                <div className="text-xs text-muted">Task: {run.prompt}</div>
                {events.map((e) => <EventLine key={e.seq} e={e} />)}
                {partial && <div className="whitespace-pre-wrap text-sm text-text">{partial}<span className="animate-pulse">▍</span></div>}
                {ACTIVE.includes(run.status) && !partial && <div className="text-xs text-muted">Droid is {run.state.replace("_", " ")}…</div>}
                <div ref={endRef} />
              </div>
              {!ACTIVE.includes(run.status) && run.session_id && (
                <div className="card flex gap-2">
                  <input className="field flex-1" aria-label="Follow-up message"
                         placeholder="Follow-up in the same Droid session" value={followUp} onChange={(e) => setFollowUp(e.target.value)} />
                  <button className="btn-primary" disabled={busy || !followUp.trim()}
                          onClick={() => start({ prompt: followUp, model, autonomy, cwd: run.cwd, continue_run_id: run.id })}>Continue</button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card">
      <div className="text-xs text-muted">{label}</div>
      <div className="text-xl font-semibold">{value}</div>
      {sub && <div className="text-xs text-muted">{sub}</div>}
    </div>
  );
}

function PerformanceTab({ runs }: { runs: AgentRun[] | null }) {
  if (!runs) return <LoadingState />;
  const done = runs.filter((r) => !ACTIVE.includes(r.status));
  if (done.length === 0) return <div className="card"><EmptyState title="No finished runs yet" /></div>;
  const ok = done.filter((r) => r.status === "succeeded").length;
  const times = done.filter((r) => r.finished_at).map((r) => new Date(r.finished_at!).getTime() - new Date(r.created_at).getTime()).sort((a, b) => a - b);
  const median = times.length ? (times[Math.floor((times.length - 1) / 2)] + times[Math.floor(times.length / 2)]) / 2 : 0;
  const byModel = new Map<string, { runs: number; ok: number; tokens: number; credits: number; location: string }>();
  for (const r of done) {
    const m = byModel.get(r.model) ?? { runs: 0, ok: 0, tokens: 0, credits: 0, location: r.model_location };
    m.runs++; if (r.status === "succeeded") m.ok++; m.tokens += tokens(r); m.credits += r.usage?.factory_credits ?? 0;
    byModel.set(r.model, m);
  }
  const statuses = done.reduce<Record<string, number>>((acc, r) => ({ ...acc, [r.status]: (acc[r.status] ?? 0) + 1 }), {});
  return (
    <div className="space-y-4">
      <p className="text-xs text-muted">Based on the latest {runs.length} runs recorded by LocalPilot.</p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Finished runs" value={String(done.length)} sub={Object.entries(statuses).map(([s, n]) => `${n} ${s}`).join(" · ")} />
        <Stat label="Succeeded" value={`${Math.round((ok / done.length) * 100)}%`} sub={`${ok} of ${done.length}`} />
        <Stat label="Median runtime" value={duration(median)} />
        <Stat label="Tokens" value={num(done.reduce((s, r) => s + tokens(r), 0))}
              sub={`${num(done.reduce((s, r) => s + (r.usage?.factory_credits ?? 0), 0))} Factory credits`} />
      </div>
      <Card title="By model">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-muted"><th className="py-1 pr-2 font-medium">Model</th><th className="pr-2 font-medium">Runs on</th><th className="pr-2 font-medium">Runs</th><th className="pr-2 font-medium">Succeeded</th><th className="pr-2 font-medium">Tokens</th><th className="font-medium">Credits</th></tr></thead>
            <tbody>
              {[...byModel.entries()].map(([m, v]) => (
                <tr key={m} className="border-t border-border">
                  <td className="py-1.5 pr-2 font-mono text-xs">{m}</td><td className="pr-2">{v.location}</td><td className="pr-2">{v.runs}</td>
                  <td className="pr-2">{v.ok}</td><td className="pr-2">{num(v.tokens)}</td><td>{num(v.credits)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function PermissionsTab() {
  const [s, setS] = useState<SettingsView | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.settings().then(setS).catch((e) => setError((e as Error).message)); }, []);
  if (error) return <ErrorBox error={error} />;
  if (!s) return <LoadingState />;
  const get = (n: string) => s.groups.flatMap((g) => g.settings).find((x) => x.name === n)?.value;
  const rows: [string, React.ReactNode][] = [
    ["Approvals", "With autonomy off, every file change and command waits for you. Low autonomy may allow low-risk edits. LocalPilot answers \"approve once\" or \"deny\"; it never saves an \"always allow\" rule."],
    ["Autonomy levels", AUTONOMY.map((a) => a.label).join(". ") + ". Medium and high are refused."],
    ["Allowed folders", (get("agent_workspaces") as string[] | undefined)?.join(", ")],
    ["Approval timeout", `${get("approval_timeout_seconds")} s, then the request is denied`],
    ["Runs at the same time", String(get("max_active_agent_runs"))],
  ];
  return (
    <Card title="Droid permissions">
      <dl className="divide-y divide-border text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="flex flex-col gap-1 py-2 sm:flex-row sm:gap-3">
            <dt className="w-44 shrink-0 text-muted">{k}</dt><dd className="min-w-0 [overflow-wrap:anywhere]">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-muted">Change these in Settings (backend/.env). Instructions, capabilities and enabling or disabling agents need the agent registry (Phase 3).</p>
    </Card>
  );
}

export default function Agent({ rest = [] }: { rest?: string[] }) {
  const tab = rest[0] === "performance" || rest[0] === "permissions" ? rest[0] : "runs";
  const selected = rest[0] === "runs" ? rest[1] ?? null : null;
  const [models, setModels] = useState<AgentModel[]>([]);
  const [workspaces, setWorkspaces] = useState<string[]>([]);
  const [defaultModel, setDefaultModel] = useState("");
  const [modelError, setModelError] = useState<string | null>(null);
  const [runs, setRuns] = useState<AgentRun[] | null>(null);
  const [pending, setPending] = useState<Approval[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refreshLists = useMemo(() => () => {
    Promise.all([agents.runs(), agents.approvals("pending")]).then(([r, p]) => { setRuns(r); setPending(p); setError(null); })
      .catch((e) => setError(`Could not load runs or approvals: ${(e as Error).message}`));
  }, []);

  useEffect(() => {
    agents.models().then((m) => {
      setModels(m.models); setWorkspaces(m.workspaces);
      setDefaultModel(m.models.find((x) => x.id === m.default)?.id ?? m.models[0]?.id ?? "");
      setModelError(null);
    }).catch((e) => setModelError(`Could not load Droid models: ${(e as Error).message}`));
    refreshLists();
    const t = setInterval(refreshLists, 3000);
    return () => clearInterval(t);
  }, [refreshLists]);

  const active = runs?.filter((r) => ACTIVE.includes(r.status)) ?? [];
  const current = active[0];
  const recentTokens = runs?.reduce((s, r) => s + tokens(r), 0) ?? 0;
  const defaultName = models.find((m) => m.id === defaultModel)?.name ?? defaultModel;

  return (
    <div className="space-y-4">
      <PageHeader title="Agents" description="Give Droid a task in an allowed folder. Strict approval is the default. Low autonomy explicitly permits some low-risk edits." />
      <ErrorBox error={error} />
      <ErrorBox error={modelError} />
      <div className="card overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-muted">
            {["Agent", "Role", "Default model", "Status", "Current task", "Runtime", "Tokens (recent runs)"].map((h) => <th key={h} className="px-4 py-2 font-medium">{h}</th>)}
          </tr></thead>
          <tbody><tr className="border-t border-border">
            <td className="px-4 py-2 font-medium">Droid</td>
            <td className="px-4 py-2">Coding agent (Factory CLI)</td>
            <td className="px-4 py-2">{defaultName || "…"}</td>
            <td className="px-4 py-2">{!runs ? "…" : <StatusBadge value={active.length ? "running" : "ok"} label={active.length ? `${active.length} active` : "Idle"} />}</td>
            <td className="max-w-56 truncate px-4 py-2">{current ? <a className="underline" href={`#/agents/runs/${current.id}`}>{current.title}</a> : <span className="text-muted">None</span>}</td>
            <td className="px-4 py-2">{current ? runtime(current.created_at, null) : "–"}</td>
            <td className="px-4 py-2">{num(recentTokens)}</td>
          </tr></tbody>
        </table>
      </div>
      <Tabs label="Agent sections" value={tab} onChange={(t) => go(t === "runs" ? "agents" : `agents/${t}`)}
            tabs={[{ id: "runs", label: "Runs", count: runs?.length }, { id: "performance", label: "Performance" }, { id: "permissions", label: "Permissions" }]} />
      {tab === "runs" && <RunsTab selected={selected} runs={runs} pending={pending} models={models} workspaces={workspaces}
                                  defaultModel={defaultModel} refreshLists={refreshLists} />}
      {tab === "performance" && <PerformanceTab runs={runs} />}
      {tab === "permissions" && <PermissionsTab />}
    </div>
  );
}
