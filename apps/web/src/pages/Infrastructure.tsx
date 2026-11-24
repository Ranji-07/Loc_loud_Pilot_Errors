import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api, type Health } from "../api";
import { go } from "../nav";
import { ErrorState, LoadingState, PageHeader, StatusBadge, Tabs } from "../ui";
import SetupGuide from "./SetupGuide";
import Usage from "./Usage";

function Logs() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.logs>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => api.logs().then((d) => { setData(d); setError(null); }).catch((e) => setError((e as Error).message)), []);
  useEffect(() => { void load(); }, [load]);
  return <div className="space-y-3">
    <button className="btn-ghost" onClick={load}>Refresh logs</button>
    <ErrorState error={error} onRetry={load} />
    {!data && !error && <LoadingState />}
    {data && <div className="card"><p className="mb-3 break-all text-xs text-muted">Latest 200 backend log lines. {data.path}</p>
      {data.lines.map((l, i) => <details key={i} className="border-t border-border py-2 text-xs">
        <summary className="cursor-pointer break-all">{l.ts ? new Date(l.ts).toLocaleString() : ""} · {l.level} · {l.msg}</summary>
        <pre className="mt-2 whitespace-pre-wrap break-all">{JSON.stringify(l.extra, null, 2)}</pre>
      </details>)}
      {!data.lines.length && <p className="text-sm text-muted">No log lines.</p>}
    </div>}
  </div>;
}

function HealthChecks() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async (force = false) => {
    setLoading(true);
    try { setHealth(await api.health(force)); setError(null); }
    catch (e) { setError(`Cannot reach the LocalPilot backend: ${(e as Error).message}`); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        {health && <StatusBadge value={health.status} label={`Overall ${health.status}`} />}
        <button className="btn-ghost ml-auto" onClick={() => load(true)} disabled={loading}><RefreshCw aria-hidden className="h-4 w-4" />{loading ? "Checking…" : "Refresh"}</button>
      </div>
      <ErrorState error={error} onRetry={() => load(true)} />
      {!health && !error && <LoadingState label="Running health checks…" />}
      {health && (
        <div className="grid gap-3 md:grid-cols-2">
          {health.checks.map((c) => (
            <div key={c.name} className="card">
              <div className="flex items-center gap-2">
                <span className="font-medium">{c.name.replaceAll("_", " ")}</span>
                <span className="ml-auto"><StatusBadge value={c.status} /></span>
              </div>
              <p className="mt-2 text-sm">{c.detail}</p>
              {c.fix && <p className="mt-1 text-xs text-muted">Fix: {c.fix}</p>}
            </div>
          ))}
        </div>
      )}
      {health && <p className="text-xs text-muted">Backend version {health.version}.</p>}
    </div>
  );
}

export default function Infrastructure({ rest }: { rest: string[] }) {
  const tab = rest[0] === "setup" || rest[0] === "resources" || rest[0] === "logs" ? rest[0] : "health";
  return (
    <div>
      <PageHeader title="Infrastructure" description="Health of this machine and its services, and guided setup with approval for every step." />
      <Tabs label="Infrastructure sections" value={tab} onChange={(t) => go(t === "setup" ? "setup" : `infrastructure/${t}`)}
            tabs={[{ id: "health", label: "Health" }, { id: "resources", label: "Resources" }, { id: "logs", label: "Logs" }, { id: "setup", label: "Setup guides" }]} />
      {tab === "health" && <HealthChecks />}
      {tab === "resources" && <Usage />}
      {tab === "logs" && <Logs />}
      {tab === "setup" && <SetupGuide />}
    </div>
  );
}
