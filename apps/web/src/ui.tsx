const STATUS_COLORS: Record<string, string> = {
  ok: "bg-emerald-900 text-emerald-300", succeeded: "bg-emerald-900 text-emerald-300",
  warn: "bg-amber-900 text-amber-300", running: "bg-sky-900 text-sky-300",
  error: "bg-rose-900 text-rose-300", failed: "bg-rose-900 text-rose-300", interrupted: "bg-rose-900 text-rose-300",
  stopped: "bg-orange-900 text-orange-300", skipped: "bg-slate-700 text-slate-300",
  info: "bg-slate-800 text-slate-300", not_configured: "bg-slate-800 text-slate-400", pending: "bg-slate-800 text-slate-400",
  low: "bg-slate-800 text-slate-300", medium: "bg-amber-900 text-amber-300", high: "bg-rose-900 text-rose-300",
};

export function Badge({ value, label }: { value: string; label?: string }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[value] ?? "bg-slate-800"}`}>
      {label ?? value.replace("_", " ")}
    </span>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return <div className="rounded border border-rose-800 bg-rose-950 p-3 text-sm text-rose-200">{error}</div>;
}
