import { useCallback, useEffect, useState } from "react";
import { api, type Alert } from "../api";
import { Badge, ErrorBox } from "../ui";

type Snapshot = Awaited<ReturnType<typeof api.usage>>;
type Summary = Awaited<ReturnType<typeof api.summary>>;
type Calls = Awaited<ReturnType<typeof api.modelCalls>>["by_model"];

export default function Usage() {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [calls, setCalls] = useState<Calls>([]);
  const [loading, setLoading] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, c] = await Promise.all([api.usage(), api.modelCalls()]);
      setSnap(s);
      setCalls(c.by_model);
      setSummary(null);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const summarize = async () => {
    if (!snap) return;
    setSummarizing(true);
    try {
      setSummary(await api.summary(snap.id));
      setCalls((await api.modelCalls()).by_model);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSummarizing(false);
    }
  };

  const local = snap?.local;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Usage</h1>
        <button className="btn-ghost ml-auto" onClick={load} disabled={loading}>{loading ? "Measuring…" : "Measure now"}</button>
        <button className="btn-primary" onClick={summarize} disabled={!snap || summarizing}>
          {summarizing ? "Asking small model…" : "Explain with small model"}
        </button>
      </div>
      <p className="text-sm text-slate-400">
        All numbers come from scripts (psutil, Ollama API, AWS CLI). The small local model only rewrites them in plain words.
      </p>
      <ErrorBox error={error} />
      {snap && (
        <div className="card space-y-2">
          <div className="font-medium">Alerts</div>
          {snap.alerts.map((a: Alert, i: number) => (
            <div key={i} className="flex gap-2 text-sm"><Badge value={a.level} /> <span>{a.text}</span></div>
          ))}
        </div>
      )}
      {summary && (
        <div className="card">
          <div className="flex items-center gap-2 font-medium">
            Small-model summary <Badge value="info" label={summary.source} />
            {summary.model && <span className="text-xs text-slate-500">{summary.model}</span>}
            {summary.duration_ms !== undefined && <span className="text-xs text-slate-500">{(summary.duration_ms / 1000).toFixed(1)} s</span>}
          </div>
          <p className="mt-2 text-sm whitespace-pre-line text-slate-200">{summary.text ?? summary.error}</p>
        </div>
      )}
      {local && (
        <div className="grid gap-3 md:grid-cols-3">
          <Stat label="CPU" value={`${local.cpu_percent}%`} sub={`${local.cpu_count} logical cores`} />
          <Stat label="RAM used" value={`${local.ram_used_percent}%`} sub={`${local.ram_available_gb} GB free of ${local.ram_total_gb} GB`} />
          <Stat label="Ollama models loaded" value={String(snap?.ollama?.loaded?.length ?? 0)}
                sub={snap?.ollama?.reachable ? "Ollama running" : "Ollama not reachable"} />
        </div>
      )}
      {local?.top_processes && (
        <Table title="Top processes (memory)" rows={local.top_processes}
               cols={Object.keys(local.top_processes[0] ?? {})} />
      )}
      {snap?.aws && (
        <div className="card text-sm space-y-1">
          <div className="font-medium">AWS</div>
          {snap.aws.reason && <div className="text-amber-300">{snap.aws.reason}</div>}
          {(snap.aws.instances ?? []).length === 0 && !snap.aws.reason && <div className="text-slate-400">No LocalPilot instances. Nothing is billing.</div>}
          {(snap.aws.instances ?? []).map((i: any) => (
            <div key={i.id}>{i.id} {i.type} <Badge value={i.state === "running" ? "warn" : "info"} label={i.state} /> ${i.hourly_usd}/h</div>
          ))}
        </div>
      )}
      {snap?.remote && (
        <div className="card text-sm">
          <div className="font-medium">Remote GPU target</div>
          <div className="text-slate-400">{snap.remote.configured ? (snap.remote.reachable ? "Reachable over SSH" : snap.remote.reason ?? "Not reachable") : "Not configured yet"}</div>
        </div>
      )}
      <Table title="Model calls logged by LocalPilot" rows={calls} cols={["model", "provider", "calls", "prompt_tokens", "completion_tokens", "cost_usd"]} />
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
      {sub && <div className="text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

function Table({ title, rows, cols }: { title: string; rows: Record<string, any>[]; cols: string[] }) {
  return (
    <div className="card">
      <div className="font-medium mb-2">{title}</div>
      {rows.length === 0 ? <div className="text-sm text-slate-500">None yet.</div> : (
        <table className="w-full text-sm">
          <thead><tr>{cols.map((c) => <th key={c} className="text-left text-xs text-slate-500 font-normal pb-1">{c.replaceAll("_", " ")}</th>)}</tr></thead>
          <tbody>{rows.map((r, i) => <tr key={i} className="border-t border-slate-800">{cols.map((c) => <td key={c} className="py-1">{String(r[c] ?? "")}</td>)}</tr>)}</tbody>
        </table>
      )}
    </div>
  );
}
