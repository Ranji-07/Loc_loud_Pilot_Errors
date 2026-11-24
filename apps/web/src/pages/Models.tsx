import { useCallback, useEffect, useState } from "react";
import { api, type ModelCatalog, type OllamaModel } from "../api";
import { num } from "../fmt";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from "../ui";

function Ollama({ title, source, search }: { title: string; source: ModelCatalog["local"]; search: string }) {
  const models = source.models.filter((m) => m.name.toLowerCase().includes(search));
  return <Card title={title}>
    <div className="mb-3 flex flex-wrap items-center gap-2 text-xs"><StatusBadge value={source.reachable ? "ok" : "unavailable"} label={source.reachable ? "Reachable" : "Not reachable"} /><code className="break-all">{source.url}</code></div>
    {!source.reachable ? <p className="text-sm text-muted">The server is not reachable. Check its service or tunnel in Infrastructure.</p> :
      !models.length ? <EmptyState title="No matching installed models" /> : <div className="space-y-2">{models.map((m: OllamaModel) => <details key={m.name} className="rounded-ui border border-border p-3">
        <summary className="cursor-pointer text-sm"><span className="font-medium">{m.name}</span> · {m.parameter_size ?? "Unknown size"} · {m.size_gb} GB on disk · {m.loaded ? "Loaded" : "Not loaded"}</summary>
        <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
          <div><dt className="text-muted">Maximum context (model metadata)</dt><dd>{m.max_context ? num(m.max_context) : "Unknown"}</dd></div>
          <div><dt className="text-muted">Configured context</dt><dd>{m.configured_context ? num(m.configured_context) : "Not specified in model parameters"}</dd></div>
          <div><dt className="text-muted">Capabilities reported by Ollama</dt><dd>{m.capabilities.join(", ") || "Unknown"} (not a reliability guarantee)</dd></div>
          <div><dt className="text-muted">Memory</dt><dd>{m.loaded ? `${m.loaded_gb} GB loaded, ${m.loaded_on_gpu_gb} GB on GPU` : "VRAM requirement unknown; disk size is not VRAM need"}</dd></div>
          <div><dt className="text-muted">Family / quantization</dt><dd>{m.family ?? "Unknown"} / {m.quantization ?? "Unknown"}</dd></div>
          <div><dt className="text-muted">Assignment</dt><dd>{m.used_by.join("; ") || "No configured assignment"}</dd></div>
        </dl>
      </details>)}</div>}
  </Card>;
}
export default function Models() {
  const [data, setData] = useState<ModelCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setBusy(true);
    try { setData(await api.models()); setError(null); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const q = search.toLowerCase();
  return <div className="space-y-4">
    <PageHeader title="Models" description="Installed Ollama models and models offered by Droid. Listing a cloud model does not verify your account can run it."
      actions={<button className="btn-ghost" disabled={busy} onClick={load}>Refresh</button>} />
    <label className="block text-sm">Search models<input className="field mt-1 w-full" value={search} onChange={(e) => setSearch(e.target.value)} /></label>
    <ErrorState error={error} onRetry={load} />
    {!data && !error && <LoadingState />}
    {data && <>
      <Ollama title="Local Ollama, this machine" source={data.local} search={q} />
      <Ollama title="Remote Ollama, tunnel" source={data.remote} search={q} />
      <Card title="Droid model choices">
        {!data.droid.available ? <p className="text-sm text-muted">{data.droid.reason}</p> :
          <div className="max-h-96 space-y-1 overflow-auto">{data.droid.models.filter((m) => `${m.name} ${m.id}`.toLowerCase().includes(q)).map((m) =>
            <details key={m.id} className="rounded-ui border border-border p-2">
              <summary className="cursor-pointer text-sm">{m.name} · {m.location === "local" ? "Local Ollama" : "Factory cloud"}{m.default ? " · Default" : ""}</summary>
              <div className="mt-2 space-y-1 break-all text-xs text-muted"><code>{m.id}</code>
                <p>{num(m.calls)} recorded runs · {num(m.credits)} Factory credits · last used {m.last_used ? new Date(m.last_used).toLocaleString() : "never recorded"}</p>
                <p>Context limits, capabilities and cloud pricing are not supplied by this API. Choose this model in Agents or Prompt Studio.</p>
              </div>
            </details>)}</div>}
      </Card>
      <Card title="How a model is chosen">{data.routing.map((r) => <div key={r.task} className="mb-3 text-sm"><h3 className="font-medium">{r.task}</h3><p>{r.route.join(" → ")}</p><p className="text-xs text-muted">{r.note}</p></div>)}</Card>
    </>}
  </div>;
}
