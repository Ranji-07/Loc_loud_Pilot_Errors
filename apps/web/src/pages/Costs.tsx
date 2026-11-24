import { useCallback, useEffect, useState } from "react";
import { api, type ModelCalls } from "../api";
import { monthStart, num } from "../fmt";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from "../ui";

export default function Costs() {
  const [calls, setCalls] = useState<ModelCalls | null>(null);
  const [window, setWindow] = useState("month");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setBusy(true); setCalls(null);
    try { setCalls(await api.modelCalls(window === "month" ? monthStart() : undefined)); setError(null); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }, [window]);
  useEffect(() => { void load(); }, [load]);
  return <div className="space-y-4">
    <PageHeader title="Costs" description="Recorded model usage, with local inference separate from paid cloud. Factory credits are not dollar charges."
      actions={<button className="btn-ghost" disabled={busy} onClick={load}>Refresh</button>} />
    <label className="block text-sm">Period<select className="field ml-3" value={window} onChange={(e) => setWindow(e.target.value)}>
      <option value="month">This month (UTC)</option><option value="all">All recorded use</option>
    </select></label>
    <ErrorState error={error} onRetry={load} />
    {!calls && !error && <LoadingState />}
    {calls && <>
      <div className="grid gap-3 sm:grid-cols-2">
        <Card title="Local inference"><p className="text-xl font-semibold">{num(calls.totals.local.calls)} calls</p><p className="text-sm text-muted">No API charge. Includes cached summaries. Electricity and hardware costs are not measured.</p></Card>
        <Card title="Cloud inference"><p className="text-xl font-semibold">{num(calls.totals.cloud.credits)} Factory credits</p><p className="text-sm text-muted">{num(calls.totals.cloud.calls)} calls. Dollar billing is not tracked for Droid, so $0 in stored cost fields does not mean free cloud use.</p></Card>
      </div>
      <Card title="Usage by model">{!calls.by_model.length ? <EmptyState title="No recorded calls in this period" /> :
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-muted">{["Model", "Provider", "Location", "Calls", "Input tokens", "Output tokens", "Credits"].map((h) => <th key={h} className="p-2 font-medium">{h}</th>)}</tr></thead>
          <tbody>{calls.by_model.map((m) => <tr key={`${m.provider}:${m.model}`} className="border-t border-border">
            <td className="p-2 font-mono text-xs">{m.model}</td><td className="p-2">{m.provider}</td><td className="p-2">{m.location}</td>
            <td className="p-2">{num(m.calls)}</td><td className="p-2">{num(m.prompt_tokens)}</td><td className="p-2">{num(m.completion_tokens)}</td><td className="p-2">{num(m.credits)}</td>
          </tr>)}</tbody>
        </table></div>}</Card>
      <Card title="Daily recorded usage (UTC)">
        {!calls.by_day.length ? <EmptyState title="No daily usage" /> : <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-muted">{["Day", "Local calls", "Cloud calls", "Factory credits"].map((h) => <th key={h} className="p-2 font-medium">{h}</th>)}</tr></thead>
          <tbody>{calls.by_day.map((d) => <tr key={d.day} className="border-t border-border"><td className="p-2">{d.day}</td><td className="p-2">{num(d.local_calls)}</td><td className="p-2">{num(d.cloud_calls)}</td><td className="p-2">{num(d.credits)}</td></tr>)}</tbody>
        </table></div>}
      </Card>
    </>}
    <Card title="Budget and GPU costs"><p className="text-sm text-muted">Monthly budgets, alerts, project breakdowns and lifetime GPU hours are not implemented yet. Current AWS instance estimates and the existing usage explanation are in <a className="underline" href="#/infrastructure/resources">Infrastructure → Resources</a>. Those estimates do not include all charges, such as storage or networking.</p></Card>
  </div>;
}
