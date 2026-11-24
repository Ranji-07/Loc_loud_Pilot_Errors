import { useEffect, useRef, useState } from "react";
import { agents, AgentEvent, AgentModel, AgentRun, Approval } from "../api";
import { Badge, ErrorBox } from "../ui";

const ACTIVE = ["starting", "running", "waiting_approval"];

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
    <div className="card border-warning space-y-2">
      <div className="flex items-center gap-2">
        <Badge value={a.risk} label={`${a.risk} risk`} />
        <span className="font-medium">{a.title}</span>
      </div>
      {(a.details.actions ?? []).map((act, i) => (
        <div key={i} className="text-xs space-y-1">
          {act.file_path && <div className="font-mono text-text">{act.file_path}</div>}
          {act.full_command && <pre className="bg-bg p-2 rounded font-mono whitespace-pre-wrap">{act.full_command}</pre>}
          {act.risk_level_reason && <div className="text-muted">{act.risk_level_reason}</div>}
          {(act.content ?? act.new_content ?? act.patch_content) && (
            <pre className="bg-bg p-2 rounded font-mono max-h-64 overflow-auto whitespace-pre-wrap">
              {act.content ?? act.patch_content ?? act.new_content}
            </pre>
          )}
        </div>
      ))}
      <input className="w-full rounded bg-bg border border-border-strong px-2 py-1 text-sm"
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
      return <div className="text-xs font-mono text-accent">→ {d.tool} {typeof d.input === "string" ? d.input.slice(0, 300) : ""}</div>;
    case "tool_result":
      return <div className={`text-xs font-mono ${d.is_error ? "text-danger" : "text-muted"} whitespace-pre-wrap max-h-40 overflow-auto`}>
        ← {d.tool}{d.is_error ? " (error)" : ""}: {String(d.content).slice(0, 1500)}</div>;
    case "approval_requested":
      return <div className="text-xs text-text">Permission requested: {d.title}</div>;
    case "approval_decided":
      return <div className="text-xs text-text">Decision: {d.decision}</div>;
    case "error":
      return <div className="text-xs text-danger">{d.message}</div>;
    case "finished":
      return <div className="text-xs text-muted">Run finished: {d.status}{d.error ? ` (${d.error})` : ""}</div>;
    default:
      return <div className="text-xs text-muted">{e.type}</div>;
  }
}

export default function Agent() {
  const [models, setModels] = useState<AgentModel[]>([]);
  const [workspaces, setWorkspaces] = useState<string[]>([]);
  const [model, setModel] = useState("");
  const [autonomy, setAutonomy] = useState("off");
  const [cwd, setCwd] = useState("");
  const [prompt, setPrompt] = useState("");
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [run, setRun] = useState<AgentRun | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [partial, setPartial] = useState("");
  const [pending, setPending] = useState<Approval[]>([]);
  const [followUp, setFollowUp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const refreshLists = () => {
    agents.runs().then(setRuns).catch(() => {});
    agents.approvals("pending").then(setPending).catch(() => {});
  };

  useEffect(() => {
    agents.models().then((m) => {
      setModels(m.models); setWorkspaces(m.workspaces); setCwd(m.workspaces[0] ?? "");
      setModel(m.models.find((x) => x.id === m.default)?.id ?? m.models[0]?.id ?? "");
    }).catch((e) => setError(`Could not load Droid models: ${(e as Error).message}`));
    refreshLists();
    const t = setInterval(refreshLists, 3000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (!selected) return;
    setEvents([]); setPartial("");
    agents.run(selected).then(setRun).catch((e) => setError((e as Error).message));
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
    es.onerror = () => es.close();
    return () => es.close();
  }, [selected]);

  useEffect(() => { endRef.current?.scrollIntoView({ block: "nearest" }); }, [events.length, partial]);

  const start = async (text: string, continueId?: string) => {
    setBusy(true); setError(null);
    try {
      const r = await agents.start({ prompt: text, model, autonomy, cwd, continue_run_id: continueId });
      setSelected(r.id); setPrompt(""); setFollowUp(""); refreshLists();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const local = models.filter((m) => m.location === "local");
  const cloud = models.filter((m) => m.location === "cloud");
  const chosen = models.find((m) => m.id === model);
  const runPending = pending.filter((a) => a.run_id === selected);
  const otherPending = pending.filter((a) => a.run_id !== selected);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Agents</h1>
      <p className="text-sm text-muted">
        Give Droid a task in an allowed folder. Every file change or command it wants to make waits here for your
        approval. LocalPilot only ever approves once; it never saves an "always allow" rule.
      </p>
      <ErrorBox error={error} />

      <div className="card space-y-3">
        <textarea className="w-full h-24 rounded bg-bg border border-border-strong p-2 text-sm"
                  placeholder="Describe the task, e.g. 'Explain what backend/localpilot/policy.py blocks'"
                  value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
          <label className="space-y-1">
            <div className="text-muted">Model</div>
            <select className="w-full rounded bg-bg border border-border-strong px-2 py-1" value={model}
                    onChange={(e) => setModel(e.target.value)}>
              {local.length > 0 && <optgroup label="Local (Ollama, no credits)">
                {local.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</optgroup>}
              <optgroup label="Factory cloud (uses Factory credits)">
                {cloud.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</optgroup>
            </select>
            <div className="text-xs text-muted">
              {chosen?.location === "local" ? "Runs on this machine through Ollama." : "Sent to Factory; usage is billed in Factory credits."}
            </div>
          </label>
          <label className="space-y-1">
            <div className="text-muted">Autonomy</div>
            <select className="w-full rounded bg-bg border border-border-strong px-2 py-1" value={autonomy}
                    onChange={(e) => setAutonomy(e.target.value)}>
              <option value="off">Off: ask before every change or command (recommended)</option>
              <option value="low">Low: Droid may make low-risk file edits without asking</option>
            </select>
          </label>
          <label className="space-y-1">
            <div className="text-muted">Folder</div>
            <select className="w-full rounded bg-bg border border-border-strong px-2 py-1" value={cwd}
                    onChange={(e) => setCwd(e.target.value)}>
              {workspaces.map((w) => <option key={w} value={w}>{w}</option>)}
            </select>
          </label>
        </div>
        <button className="btn-primary" disabled={busy || !prompt.trim() || !model} onClick={() => start(prompt)}>Start Droid</button>
      </div>

      {otherPending.length > 0 && (
        <div className="card border-warning text-sm">
          {otherPending.length} approval(s) waiting on other runs:{" "}
          {otherPending.map((a) => <button key={a.id} className="underline mr-2" onClick={() => setSelected(a.run_id)}>{a.title}</button>)}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card space-y-1 max-h-[70vh] overflow-auto">
          <div className="text-sm text-muted mb-2">Runs</div>
          {runs.length === 0 && <div className="text-sm text-muted">No runs yet.</div>}
          {runs.map((r) => (
            <button key={r.id} onClick={() => setSelected(r.id)}
                    className={`w-full text-left rounded px-2 py-1.5 text-sm ${selected === r.id ? "bg-surface-2" : "hover:bg-surface-2"}`}>
              <div className="flex items-center gap-2"><Badge value={r.status} /><span className="truncate">{r.title}</span></div>
              <div className="text-xs text-muted">{new Date(r.created_at).toLocaleString()} · {r.model_location}</div>
            </button>
          ))}
        </div>

        <div className="lg:col-span-2 space-y-3">
          {!run && <div className="card text-sm text-muted">Start a task or pick a run.</div>}
          {run && (
            <>
              <div className="card space-y-1 text-sm">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge value={run.status} /><span className="font-medium">{run.title}</span>
                  {ACTIVE.includes(run.status) && <button className="btn-danger ml-auto" onClick={() => agents.stop(run.id).then(setRun).catch((e) => setError((e as Error).message))}>Stop</button>}
                </div>
                <div className="text-xs text-muted">
                  {run.model} ({run.model_location}) · autonomy {run.autonomy} · {run.cwd} {credits(run) && `· ${credits(run)}`}
                </div>
                {run.error && <div className="text-xs text-danger">{run.error}</div>}
              </div>
              {runPending.map((a) => <ApprovalCard key={a.id} a={a} onDone={refreshLists} />)}
              <div className="card space-y-2 max-h-[55vh] overflow-auto">
                <div className="text-xs text-muted">Task: {run.prompt}</div>
                {events.map((e) => <EventLine key={e.seq} e={e} />)}
                {partial && <div className="whitespace-pre-wrap text-sm text-text">{partial}<span className="animate-pulse">▍</span></div>}
                {ACTIVE.includes(run.status) && !partial && <div className="text-xs text-muted">Droid is {run.state.replace("_", " ")}…</div>}
                <div ref={endRef} />
              </div>
              {!ACTIVE.includes(run.status) && run.session_id && (
                <div className="card flex gap-2">
                  <input className="flex-1 rounded bg-bg border border-border-strong px-2 py-1 text-sm"
                         placeholder="Follow-up in the same Droid session" value={followUp} onChange={(e) => setFollowUp(e.target.value)} />
                  <button className="btn-primary" disabled={busy || !followUp.trim()} onClick={() => start(followUp, run.id)}>Continue</button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
