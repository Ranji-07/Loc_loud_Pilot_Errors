import type { ReactNode } from "react";
import { AlertTriangle, Inbox, Loader2, Lock } from "lucide-react";

type Tone = "success" | "warning" | "danger" | "accent" | "neutral";

const TONES: Record<string, Tone> = {
  ok: "success", succeeded: "success", approved: "success", passed: "success",
  warn: "warning", waiting_approval: "warning", medium: "warning", pending: "warning", stopped: "warning",
  error: "danger", failed: "danger", interrupted: "danger", high: "danger", denied: "danger", blocked: "danger",
  running: "accent", starting: "accent",
};

const DOT: Record<Tone, string> = {
  success: "bg-success", warning: "bg-warning", danger: "bg-danger", accent: "bg-accent", neutral: "bg-muted",
};
const SOFT: Record<Tone, string> = {
  success: "bg-success-soft", warning: "bg-warning-soft", danger: "bg-danger-soft", accent: "bg-accent-soft", neutral: "bg-surface-2",
};

/** Text stays in --text so it meets AA in both themes; the semantic colour is carried by the dot and fill. */
export function StatusBadge({ value, label, tone }: { value: string; label?: string; tone?: Tone }) {
  const t = tone ?? TONES[value] ?? "neutral";
  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-ui px-2 py-0.5 text-xs font-medium text-text ${SOFT[t]}`}>
      <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${DOT[t]}`} />
      {label ?? value.replaceAll("_", " ")}
    </span>
  );
}

export const Badge = StatusBadge;

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-start gap-3 pb-4">
      <div className="min-w-0 flex-1">
        <h1 className="text-xl font-semibold">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}

export function ErrorState({ error, onRetry }: { error: string | null; onRetry?: () => void }) {
  if (!error) return null;
  return (
    <div role="alert" className="flex items-start gap-2 rounded-ui border border-danger bg-danger-soft p-3 text-sm text-text">
      <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
      <span className="flex-1">{error}</span>
      {onRetry && <button className="btn-ghost py-0.5" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export const ErrorBox = ErrorState;

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 p-3 text-sm text-muted">
      <Loader2 aria-hidden className="h-4 w-4 animate-spin" /> {label}
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 p-6 text-center">
      <Inbox aria-hidden className="h-5 w-5 text-muted" />
      <div className="text-sm font-medium">{title}</div>
      {children && <div className="max-w-md text-sm text-muted">{children}</div>}
      {action}
    </div>
  );
}

export function Card({ title, actions, children, className = "" }: { title?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card min-w-0 ${className}`} aria-label={title}>
      {(title || actions) && (
        <div className="mb-3 flex items-center gap-2">
          {title && <h2 className="text-sm font-semibold">{title}</h2>}
          {actions && <div className="ml-auto flex items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange, label }: {
  tabs: { id: T; label: string; count?: number }[]; value: T; onChange: (id: T) => void; label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="mb-4 flex gap-1 border-b border-border">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}
                className={`-mb-px border-b-2 px-3 py-2 text-sm ${value === t.id ? "border-accent font-medium text-text" : "border-transparent text-muted hover:text-text"}`}>
          {t.label}{t.count !== undefined && <span className="ml-1.5 rounded-ui bg-surface-2 px-1.5 text-xs">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

/** A screen whose backend does not exist yet. Says what is missing instead of showing fake data. */
export function Unavailable({ title, description, needs, phase }: { title: string; description: string; needs: string[]; phase: string }) {
  return (
    <div>
      <PageHeader title={title} description={description} />
      <div className="card flex flex-col items-start gap-3">
        <StatusBadge value="unavailable" label={`Not available yet (${phase})`} tone="neutral" />
        <div className="flex items-start gap-2 text-sm">
          <Lock aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-muted" />
          <div>
            <p>This screen needs backend features that are not built yet:</p>
            <ul className="mt-1 list-disc pl-5 text-muted">{needs.map((n) => <li key={n}>{n}</li>)}</ul>
          </div>
        </div>
        <p className="text-xs text-muted">Tracked in docs/PENDING.md.</p>
      </div>
    </div>
  );
}
