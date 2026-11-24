import { useCallback, useEffect, useState } from "react";
import { agents, type Approval } from "../api";
import { go } from "../nav";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge, Tabs } from "../ui";
import { ApprovalCard } from "./Agent";

function Approvals() {
  const [items, setItems] = useState<Approval[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const load = useCallback(() => {
    agents.approvals().then((a) => { setItems(a); setError(null); }).catch((e) => setError((e as Error).message));
  }, []);
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, [load]);
  if (error) return <ErrorState error={error} onRetry={load} />;
  if (!items) return <LoadingState />;
  const pending = items.filter((a) => a.status === "pending");
  const done = items.filter((a) => a.status !== "pending" && `${a.title} ${a.status} ${a.comment ?? ""}`.toLowerCase().includes(search.toLowerCase()));
  return (
    <div className="space-y-4">
      <section aria-label="Pending approvals" className="space-y-3">
        <h2 className="text-sm font-semibold">Waiting for you ({pending.length})</h2>
        {pending.length === 0 && <div className="card"><EmptyState title="Nothing is waiting for approval">Droid asks here before it changes a file or runs a command.</EmptyState></div>}
        {pending.map((a) => (
          <div key={a.id} className="space-y-1">
            <a className="text-xs text-muted underline" href={`#/agents/runs/${a.run_id}`}>From Droid run {a.run_id?.slice(0, 8)}</a>
            <ApprovalCard a={a} onDone={load} />
          </div>
        ))}
      </section>
      <section aria-label="Approval history" className="card overflow-x-auto">
        <h2 className="mb-2 text-sm font-semibold">History</h2>
        <label className="mb-3 block text-xs">Search recent approval history
          <input className="field mt-1 w-full" value={search} onChange={(e) => setSearch(e.target.value)} />
        </label>
        <p className="mb-2 text-xs text-muted">Latest 100 approvals. Full recorded outcomes are searchable and paginated in <a className="underline" href="#/history">History</a>.</p>
        {done.length === 0 ? <p className="text-sm text-muted">No decisions yet.</p> : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-muted"><th className="py-1 pr-2 font-medium">Requested</th><th className="pr-2 font-medium">Action</th><th className="pr-2 font-medium">Risk</th><th className="pr-2 font-medium">Outcome</th><th className="font-medium">By</th></tr></thead>
            <tbody>
              {done.map((a) => (
                <tr key={a.id} className="border-t border-border align-top">
                  <td className="whitespace-nowrap py-1.5 pr-2 text-muted">{new Date(a.created_at).toLocaleString()}</td>
                  <td className="pr-2">{a.title}{a.comment && <div className="text-xs text-muted">{a.comment}</div>}</td>
                  <td className="pr-2"><StatusBadge value={a.risk} /></td>
                  <td className="pr-2"><StatusBadge value={a.status} /></td>
                  <td className="text-muted">{a.decided_by ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default function Decisions({ tab }: { tab: "approvals" | "decisions" }) {
  return (
    <div>
      <PageHeader title="Decisions" description="Approve or deny what agents want to do, and review every outcome." />
      <Tabs label="Decision types" value={tab} onChange={(t) => go(`decisions/${t}`)}
            tabs={[{ id: "approvals", label: "Approvals" }, { id: "decisions", label: "Decisions" }]} />
      {tab === "approvals" ? <Approvals /> : (
        <div className="card">
          <EmptyState title="Engineering decisions are not available yet">
            Architecture, model, dependency and budget decisions need a decisions store (Phase 3). Tracked in docs/PENDING.md.
          </EmptyState>
        </div>
      )}
    </div>
  );
}
