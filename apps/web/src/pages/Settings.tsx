import { useCallback, useEffect, useState } from "react";
import { api, type SettingsView } from "../api";
import { getThemeChoice, setThemeChoice, type ThemeChoice } from "../theme";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from "../ui";

const display = (v: unknown) => v === null ? "Not configured" : typeof v === "object" ? JSON.stringify(v, null, 2) : String(v);
export default function Settings() {
  const [data, setData] = useState<SettingsView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [theme, setTheme] = useState(getThemeChoice);
  const load = useCallback(async () => {
    try { setData(await api.settings()); setError(null); } catch (e) { setError((e as Error).message); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const changed = () => setTheme(getThemeChoice());
    window.addEventListener("localpilot-theme", changed);
    return () => window.removeEventListener("localpilot-theme", changed);
  }, []);
  const q = search.toLowerCase();
  const groups = data?.groups.map((g) => ({ ...g, settings: g.settings.filter((r) => `${g.title} ${r.name.replaceAll("_", " ")} ${r.description} ${r.env}`.toLowerCase().includes(q)) })).filter((g) => g.settings.length);
  return <div className="space-y-4">
    <PageHeader title="Settings" description="Backend configuration is read-only. Appearance is saved in this browser. Secrets are hidden." />
    <Card title="Appearance"><label className="text-sm">Theme<select className="field ml-3" value={theme} onChange={(e) => setThemeChoice(e.target.value as ThemeChoice)}>
      <option value="dark">Dark</option><option value="light">Light</option><option value="system">System</option>
    </select></label></Card>
    <label className="block text-sm">Search settings<input className="field mt-1 w-full" value={search} onChange={(e) => setSearch(e.target.value)} /></label>
    <ErrorState error={error} onRetry={load} />
    {!data && !error && <LoadingState />}
    {data && <p className="text-sm text-muted">{data.how_to_change} There are no Save or Reset controls because this page does not write configuration.</p>}
    {groups?.length === 0 && <EmptyState title="No matching settings" />}
    {groups?.map((g) => <Card key={g.title} title={g.title}><dl className="divide-y divide-border">
      {g.settings.map((r) => <div key={r.name} className="grid gap-2 py-3 md:grid-cols-2">
        <dt><span className="text-sm font-medium">{r.name.replaceAll("_", " ")}</span><p className="mt-1 text-xs text-muted">{r.description}</p>
          <code className="mt-1 block break-all text-xs text-muted">{r.env}</code></dt>
        <dd className="min-w-0"><pre className="whitespace-pre-wrap break-all rounded-ui bg-surface-2 p-2 text-xs">{display(r.value)}</pre>
          <details className="mt-1 text-xs text-muted"><summary className="cursor-pointer">{r.is_default ? "Default value" : "Changed from default"}</summary><pre className="mt-1 whitespace-pre-wrap break-all">{display(r.default)}</pre></details>
        </dd>
      </div>)}</dl></Card>)}
  </div>;
}
