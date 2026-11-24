import { useCallback, useEffect, useState } from "react";
import { api, type AuditFilter, type AuditRow } from "../api";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "../ui";

const SIZE = 25;
export default function Audit() {
  const [events, setEvents] = useState<AuditRow[] | null>(null);
  const [filter, setFilter] = useState<AuditFilter>({});
  const [search, setSearch] = useState("");
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [cursors, setCursors] = useState<(number | undefined)[]>([undefined]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setEvents(await api.auditPage({ ...filter, before: cursors[cursors.length - 1], limit: SIZE + 1 })); }
    catch (e) { setError((e as Error).message); } finally { setLoading(false); }
  }, [filter, cursors]);
  useEffect(() => { void load(); }, [load]);
  const rows = events?.slice(0, SIZE) ?? [];
  return (
    <div className="space-y-4">
      <PageHeader title="History" description="Recorded agent runs, approvals and setup steps. Model use is also recorded on each run. Project history and Git recovery are not available yet." />
      <form className="card flex flex-wrap items-end gap-3" onSubmit={(e) => {
        e.preventDefault(); setCursors([undefined]);
        setFilter({ q: search, action, actor, since: since ? `${since}T00:00:00Z` : undefined,
          until: until ? new Date(Date.parse(`${until}T00:00:00Z`) + 86400000).toISOString() : undefined });
      }}>
        <label className="min-w-0 flex-1 text-xs">Search action or target<input className="field mt-1 w-full" value={search} onChange={(e) => setSearch(e.target.value)} /></label>
        <label className="text-xs">Category<select className="field mt-1 block" value={action} onChange={(e) => setAction(e.target.value)}>
          <option value="">All</option><option value="agent.">Agents</option><option value="approval.">Approvals</option><option value="step.">Setup steps</option><option value="runbook.">Setup runs</option><option value="server.">Server</option>
        </select></label>
        <label className="text-xs">Actor<select className="field mt-1 block" value={actor} onChange={(e) => setActor(e.target.value)}>
          <option value="">All</option><option value="user">User</option><option value="system">System</option><option value="agent">Agent</option>
        </select></label>
        <label className="text-xs">From (UTC)<input type="date" className="field mt-1 block" value={since} max={until || undefined} onChange={(e) => setSince(e.target.value)} /></label>
        <label className="text-xs">Through (UTC)<input type="date" className="field mt-1 block" value={until} min={since || undefined} onChange={(e) => setUntil(e.target.value)} /></label>
        <button className="btn-primary" disabled={loading}>Apply filters</button>
        <button type="button" className="btn-ghost" onClick={() => { setSearch(""); setAction(""); setActor(""); setSince(""); setUntil(""); setFilter({}); setCursors([undefined]); }}>Clear</button>
      </form>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <a className="btn-ghost" href={api.auditExportUrl("csv", filter)}>Export CSV</a>
        <a className="btn-ghost" href={api.auditExportUrl("json", filter)}>Export JSON</a>
        <span className="text-muted">Exports include the newest 10,000 matching events.</span>
      </div>
      <ErrorState error={error} onRetry={load} />
      {loading ? <LoadingState /> : !error && <div className="card">
        {!rows.length ? <EmptyState title="No matching events">Try clearing the filters.</EmptyState> :
          <ol className="divide-y divide-border">{rows.map((e) => <li key={e.id} className="py-3 text-sm" data-event-id={e.id}>
            <div className="flex flex-wrap gap-x-3 gap-y-1"><span className="font-mono">{e.action}</span><time className="text-xs text-muted" dateTime={e.at}>{new Date(e.at).toLocaleString()}</time><span className="text-xs text-muted">{e.actor}</span></div>
            <div className="mt-1 break-all font-mono text-xs">{e.action.startsWith("agent.") ? <a className="underline" href={`#/agents/runs/${e.target}`}>{e.target}</a> : e.target}</div>
            {Object.keys(e.detail ?? {}).length > 0 && <details className="mt-1 text-xs"><summary className="cursor-pointer text-muted">Details</summary><pre className="mt-2 whitespace-pre-wrap break-all">{JSON.stringify(e.detail, null, 2)}</pre></details>}
          </li>)}</ol>}
      </div>}
      <div className="flex items-center gap-3">
        <button className="btn-ghost" disabled={loading || cursors.length === 1} onClick={() => setCursors((c) => c.slice(0, -1))}>Newer</button>
        <span className="text-sm text-muted">Page {cursors.length}</span>
        <button className="btn-ghost" disabled={loading || !!error || !events || events.length <= SIZE} onClick={() => setCursors((c) => [...c, rows[rows.length - 1].id])}>Older</button>
      </div>
    </div>
  );
}
