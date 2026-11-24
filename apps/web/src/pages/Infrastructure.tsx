import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api, type Health } from "../api";
import { go } from "../nav";
import { ErrorState, LoadingState, PageHeader, StatusBadge, Tabs } from "../ui";
import SetupGuide from "./SetupGuide";

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
  const tab = rest[0] === "setup" ? "setup" : "health";
  return (
    <div>
      <PageHeader title="Infrastructure" description="Health of this machine and its services, and guided setup with approval for every step." />
      <Tabs label="Infrastructure sections" value={tab} onChange={(t) => go(t === "setup" ? "setup" : "infrastructure")}
            tabs={[{ id: "health", label: "Health" }, { id: "setup", label: "Setup guides" }]} />
      {tab === "health" ? <HealthChecks /> : <SetupGuide />}
    </div>
  );
}
