import { useCallback, useEffect, useMemo, useState } from "react";
import { agents, type AgentModel, type AgentRun } from "../api";
import { ago, num } from "../fmt";
import { go } from "../nav";
import { Card, ErrorState, LoadingState, PageHeader } from "../ui";
import { ModelSelect } from "./Agent";

const VARIABLE = /\{\{\s*([A-Za-z_][\w-]*)\s*\}\}/g;

export default function PromptStudio() {
  const [models, setModels] = useState<AgentModel[]>([]);
  const [runs, setRuns] = useState<AgentRun[] | null>(null);
  const [folders, setFolders] = useState<string[]>([]);
  const [folder, setFolder] = useState("");
  const [model, setModel] = useState("");
  const [text, setText] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      const [m, r] = await Promise.all([agents.models(), agents.runs()]);
      setModels(m.models); setFolders(m.workspaces); setRuns(r);
      setModel((v) => v || m.default); setFolder((v) => v || m.workspaces[0] || "");
      setError(null);
    } catch (e) { setError((e as Error).message); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const vars = useMemo(() => [...new Set([...text.matchAll(VARIABLE)].map((m) => m[1]))], [text]);
  const final = text.replace(VARIABLE, (_, name: string) => values[name] ?? "");
  const missing = vars.filter((v) => !values[v]?.trim());
  const chosen = models.find((m) => m.id === model);
  const earlier = (runs ?? []).filter((r) => r.model === model && r.usage?.factory_credits > 0);
  const average = earlier.length ? earlier.reduce((s, r) => s + r.usage.factory_credits, 0) / earlier.length : null;
  const run = async () => {
    setBusy(true); setError(null);
    try {
      const r = await agents.start({ prompt: final, model, cwd: folder, autonomy: "off" });
      go(`agents/runs/${r.id}`);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-4">
      <PageHeader title="Prompt Studio" description="Write a prompt, fill its variables and run it with Droid. Commands and file changes still require approval." />
      <ErrorState error={error} onRetry={load} />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[13rem_minmax(0,1fr)_16rem]">
        <aside className="order-3 min-w-0 space-y-3 xl:order-1" aria-label="Prompt library">
          <Card title="Recent prompts">
            {!runs && !error ? <LoadingState /> : !runs?.length ? <p className="text-sm text-muted">No prompts recorded.</p> :
              <ul className="max-h-80 space-y-1 overflow-auto">{runs.slice(0, 20).map((r) =>
                <li key={r.id}><button className="w-full rounded-ui p-2 text-left hover:bg-surface-2" onClick={() => { setText(r.prompt); setModel(r.model); }}>
                  <div className="truncate text-sm">{r.title}</div><div className="text-xs text-muted">{ago(r.created_at)} · {r.model_location}</div>
                </button></li>)}</ul>}
          </Card>
          <Card title="Templates and versions"><p className="text-sm text-muted">Saving, templates, versions and output comparison are not available yet. They need prompt storage (Phase 2).</p></Card>
        </aside>
        <section className="order-1 min-w-0 space-y-3 xl:order-2" aria-label="Prompt editor">
          <Card>
            <label htmlFor="prompt-editor" className="mb-2 block text-sm font-semibold">Prompt</label>
            <textarea id="prompt-editor" className="field h-72 w-full p-3 font-mono" placeholder="Describe your task. Use {{file}} for a reusable variable."
              value={text} onChange={(e) => setText(e.target.value)} />
            <p className="mt-2 text-xs text-muted">{num(final.length)} characters · roughly {num(Math.ceil(final.length / 4))} prompt tokens (4 characters per token, not a tokenizer).</p>
          </Card>
          <Card title={`Variables (${vars.length})`}>
            {!vars.length ? <p className="text-sm text-muted">Write {"{{name}}"} in the prompt to add a variable.</p> :
              <div className="grid gap-2 sm:grid-cols-2">{vars.map((v) => <label key={v} className="text-sm">{v}
                <input className="field mt-1 w-full" value={values[v] ?? ""} onChange={(e) => setValues((x) => ({ ...x, [v]: e.target.value }))} />
              </label>)}</div>}
          </Card>
          <details className="card text-sm"><summary className="cursor-pointer">Context attachments, not available yet</summary>
            <p className="mt-2 text-muted">The context engine is pending in Phase 2. You can name files in your prompt; Droid reads them from the selected folder.</p>
          </details>
        </section>
        <aside className="order-2 min-w-0 space-y-3 xl:order-3" aria-label="Execution settings">
          <Card>
            <label htmlFor="prompt-model" className="mb-2 block text-sm font-semibold">Model</label>
            {models.length ? <ModelSelect id="prompt-model" models={models} value={model} onChange={setModel} /> : !error && <LoadingState />}
            <p className="mt-3 rounded-ui bg-surface-2 p-2 text-xs">
              {chosen?.location === "local" ? "Local Ollama: no Factory credits. CPU runs can take many minutes." :
                average !== null ? `Historical average: ${num(Math.round(average))} Factory credits across ${earlier.length} runs with this model. This is not a quote.` : "Credit estimate unavailable: no recorded runs with this model."}
              {" "}Droid instructions, file contents and output add tokens beyond your prompt.
            </p>
            <details className="mt-3 text-sm"><summary className="cursor-pointer text-muted">Advanced</summary>
              <label className="mt-2 block">Folder<select className="field mt-1 w-full" value={folder} onChange={(e) => setFolder(e.target.value)}>
                {folders.map((f) => <option key={f}>{f}</option>)}</select></label>
              <p className="mt-2 text-xs text-muted">Strict approval: autonomy off.</p>
            </details>
            <button className="btn-primary mt-4 w-full justify-center" disabled={busy || !model || !folder || !final.trim() || missing.length > 0} onClick={run}>
              {busy ? "Starting…" : "Run with Droid"}</button>
            {missing.length > 0 && <p className="mt-2 text-xs text-muted">Fill in: {missing.join(", ")}</p>}
          </Card>
        </aside>
      </div>
      {vars.length > 0 && <Card title="Prompt that will be sent"><pre className="whitespace-pre-wrap break-words text-xs">{final}</pre></Card>}
    </div>
  );
}
