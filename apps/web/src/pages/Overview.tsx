import { useCallback, useEffect, useState } from "react";
import { api, type Health } from "../api";
import { Badge, ErrorBox } from "../ui";

export default function Overview() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setHealth(await api.health());
      setError(null);
    } catch (e) {
      setError(`Cannot reach the LocalPilot backend: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Overview</h1>
        {health && <Badge value={health.status} />}
        <button className="btn-ghost ml-auto" onClick={load} disabled={loading}>{loading ? "Checking…" : "Refresh"}</button>
      </div>
      <ErrorBox error={error} />
      {health && (
        <div className="grid gap-3 md:grid-cols-2">
          {health.checks.map((c) => (
            <div key={c.name} className="card">
              <div className="flex items-center gap-2">
                <span className="font-medium">{c.name.replace("_", " ")}</span>
                <span className="ml-auto"><Badge value={c.status} /></span>
              </div>
              <p className="mt-2 text-sm text-slate-300">{c.detail}</p>
              {c.hint && <p className="mt-1 text-xs text-slate-500">{c.hint}</p>}
            </div>
          ))}
        </div>
      )}
      {health && <p className="text-xs text-slate-500">Backend version {health.version}. Refreshes every 15 seconds.</p>}
    </div>
  );
}
