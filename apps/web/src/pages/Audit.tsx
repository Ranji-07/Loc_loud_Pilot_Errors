import { useEffect, useState } from "react";
import { api } from "../api";
import { ErrorBox } from "../ui";

type Event = Awaited<ReturnType<typeof api.audit>>[number];

export default function Audit() {
  const [events, setEvents] = useState<Event[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.audit().then(setEvents).catch((e) => setError((e as Error).message)); }, []);
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">History</h1>
      <p className="text-sm text-muted">Every agent run, approval decision and setup step is recorded here (latest 200 events).</p>
      <ErrorBox error={error} />
      <div className="card overflow-auto">
        <table className="w-full text-xs">
          <thead><tr className="text-left text-muted"><th>Time</th><th>Actor</th><th>Action</th><th>Target</th><th>Detail</th></tr></thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id} className="border-t border-border align-top">
                <td className="py-1 pr-2 whitespace-nowrap">{new Date(e.at).toLocaleString()}</td>
                <td className="pr-2">{e.actor}</td>
                <td className="pr-2 whitespace-nowrap">{e.action}</td>
                <td className="pr-2 font-mono">{e.target}</td>
                <td className="font-mono break-all">{e.detail && Object.keys(e.detail).length ? JSON.stringify(e.detail) : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
