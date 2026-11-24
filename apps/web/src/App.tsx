import { lazy, Suspense, useEffect, useState } from "react";
import { ChevronDown, Menu, Monitor, Moon, Search, Sun, X } from "lucide-react";
import { agents, api, type Health } from "./api";
import { CommandPalette } from "./CommandPalette";
import { NAV, parseHash } from "./nav";
import { getThemeChoice, setThemeChoice, type ThemeChoice } from "./theme";
import { LoadingState, Unavailable } from "./ui";
const Overview = lazy(() => import("./pages/Overview"));
const Agent = lazy(() => import("./pages/Agent"));
const Decisions = lazy(() => import("./pages/Decisions"));
const Audit = lazy(() => import("./pages/Audit"));
const Infrastructure = lazy(() => import("./pages/Infrastructure"));
const Costs = lazy(() => import("./pages/Costs"));
const PromptStudio = lazy(() => import("./pages/PromptStudio"));
const Models = lazy(() => import("./pages/Models"));
const Settings = lazy(() => import("./pages/Settings"));

const UNAVAILABLE: Record<string, { title: string; description: string; needs: string[]; phase: string }> = {
  projects: { title: "Projects", description: "Register repositories and keep their instructions, architecture and tasks together.",
              needs: ["Project registration and storage", "Repository import (Git)"], phase: "Phase 2" },
  tasks: { title: "Tasks", description: "Objectives, plans, progress and results for agent work.",
           needs: ["Task model and API (agent runs are on the Agents page today)"], phase: "Phase 2" },
  knowledge: { title: "Knowledge", description: "Architecture, decisions, documentation and codebase summaries with source hashes.",
               needs: ["Project memory with commit references", "Context engine"], phase: "Phase 2" },
};

function ThemeSwitch() {
  const [choice, setChoice] = useState<ThemeChoice>(getThemeChoice);
  useEffect(() => {
    const on = () => setChoice(getThemeChoice());
    window.addEventListener("localpilot-theme", on);
    return () => window.removeEventListener("localpilot-theme", on);
  }, []);
  const opts: { id: ThemeChoice; label: string; Icon: typeof Sun }[] = [
    { id: "dark", label: "Dark", Icon: Moon }, { id: "light", label: "Light", Icon: Sun }, { id: "system", label: "System", Icon: Monitor },
  ];
  return (
    <div role="radiogroup" aria-label="Theme" className="flex rounded-ui border border-border p-0.5">
      {opts.map(({ id, label, Icon }) => (
        <button key={id} role="radio" aria-checked={choice === id} title={label}
                onClick={() => setThemeChoice(id)}
                className={`flex flex-1 items-center justify-center gap-1 rounded-ui py-1 text-xs ${choice === id ? "bg-surface-2 text-text" : "text-muted hover:text-text"}`}>
          <Icon aria-hidden className="h-3.5 w-3.5" />{label}
        </button>
      ))}
    </div>
  );
}

function Sidebar({ page, pending, health, onSearch, onNavigate }: {
  page: string; pending: number; health: Health | null | "offline"; onSearch: () => void; onNavigate: () => void;
}) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() => JSON.parse(localStorage.getItem("localpilot.nav") ?? "{}"));
  const toggle = (id: string) => setCollapsed((c) => {
    const next = { ...c, [id]: !c[id] };
    localStorage.setItem("localpilot.nav", JSON.stringify(next));
    return next;
  });
  const issues = health && health !== "offline" ? health.checks.filter((c) => c.status === "warn" || c.status === "error") : [];
  const dot = health === "offline" || health?.status === "error" ? "bg-danger" : issues.length ? "bg-warning" : health ? "bg-success" : "bg-muted";
  const statusText = health === "offline" ? "Backend offline" : !health ? "Checking…" : issues.length ? `${issues.length} check${issues.length > 1 ? "s" : ""} need attention` : "All checks OK";
  return (
    <div className="flex h-full flex-col gap-3 p-3">
      <div className="px-2 pt-1 text-base font-semibold">LocalPilot</div>
      <div className="rounded-ui border border-border px-2 py-1.5 text-xs" title="Multiple projects arrive in Phase 2">
        <div className="text-muted">Project</div>
        <div className="truncate font-medium">Loc_loud_Pilot_Errors</div>
      </div>
      <button onClick={onSearch} className="flex items-center gap-2 rounded-ui border border-border-strong px-2 py-1.5 text-sm text-muted hover:text-text">
        <Search aria-hidden className="h-4 w-4" /> Search <kbd className="ml-auto rounded border border-border px-1 text-[10px]">Ctrl K</kbd>
      </button>
      <nav aria-label="Main" className="flex-1 space-y-2 overflow-auto">
        {NAV.map((g) => (
          <div key={g.id}>
            <button onClick={() => toggle(g.id)} aria-expanded={!collapsed[g.id]}
                    className="flex w-full items-center px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted hover:text-text">
              {g.label}<ChevronDown aria-hidden className={`ml-auto h-3.5 w-3.5 ${collapsed[g.id] ? "-rotate-90" : ""}`} />
            </button>
            {!collapsed[g.id] && g.items.map((i) => (
              <a key={i.id} href={`#/${i.id}`} onClick={onNavigate} aria-current={page === i.id ? "page" : undefined}
                 className={`flex items-center gap-2 rounded-ui px-2 py-1.5 text-sm ${page === i.id ? "bg-surface-2 font-medium text-text" : "text-muted hover:bg-surface-2 hover:text-text"}`}>
                <i.icon aria-hidden className={`h-4 w-4 ${page === i.id ? "text-accent" : ""}`} />
                <span className="flex-1">{i.label}</span>
                {i.id === "decisions" && pending > 0 && (
                  <span className="rounded-ui bg-warning-soft px-1.5 text-xs text-text" aria-label={`${pending} pending approvals`}>{pending}</span>
                )}
                {!i.available && <span className="text-[10px] text-muted">soon</span>}
              </a>
            ))}
          </div>
        ))}
      </nav>
      <a href="#/infrastructure" onClick={onNavigate} className="flex items-center gap-2 rounded-ui px-2 py-1.5 text-xs hover:bg-surface-2"
         title={issues.map((c) => `${c.name}: ${c.detail}`).join("\n") || undefined}>
        <span aria-hidden className={`h-2 w-2 rounded-full ${dot}`} />{statusText}
      </a>
      <ThemeSwitch />
    </div>
  );
}

export default function App() {
  const [route, setRoute] = useState(parseHash);
  const [palette, setPalette] = useState(false);
  const [menu, setMenu] = useState(false);
  const [pending, setPending] = useState(0);
  const [health, setHealth] = useState<Health | null | "offline">(null);

  useEffect(() => {
    const on = () => setRoute(parseHash());
    window.addEventListener("hashchange", on);
    const key = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((p) => !p); }
    };
    window.addEventListener("keydown", key);
    return () => { window.removeEventListener("hashchange", on); window.removeEventListener("keydown", key); };
  }, []);

  useEffect(() => {
    const loadPending = () => agents.approvals("pending").then((a) => setPending(a.length)).catch(() => {});
    const loadHealth = () => api.health().then(setHealth).catch(() => setHealth("offline"));
    loadPending(); loadHealth();
    const t1 = setInterval(loadPending, 5000);
    const t2 = setInterval(loadHealth, 30000);
    return () => { clearInterval(t1); clearInterval(t2); };
  }, []);

  const { page, rest } = route;
  const sidebar = <Sidebar page={page} pending={pending} health={health} onSearch={() => setPalette(true)} onNavigate={() => setMenu(false)} />;

  return (
    <div className="flex min-h-screen">
      <a href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}
         className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded-ui focus:bg-surface focus:px-3 focus:py-2">Skip to content</a>
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 border-r border-border bg-surface lg:block">{sidebar}</aside>
      {menu && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMenu(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 border-r border-border bg-surface">
            <button className="btn-ghost absolute right-2 top-2 px-2" aria-label="Close menu" onClick={() => setMenu(false)}><X className="h-4 w-4" /></button>
            {sidebar}
          </aside>
        </div>
      )}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 border-b border-border bg-surface px-3 py-2 lg:hidden">
          <button className="btn-ghost px-2" aria-label="Open menu" onClick={() => setMenu(true)}><Menu className="h-4 w-4" /></button>
          <span className="font-semibold">LocalPilot</span>
        </div>
        <main id="main" tabIndex={-1} className="mx-auto max-w-6xl p-4 outline-none lg:p-6">
          <Suspense fallback={<LoadingState />}>
          {page === "overview" && <Overview />}
          {page === "agents" && <Agent rest={rest} />}
          {page === "decisions" && <Decisions tab={rest[0] === "decisions" ? "decisions" : "approvals"} />}
          {page === "history" && <Audit />}
          {page === "infrastructure" && <Infrastructure rest={rest} />}
          {page === "costs" && <Costs />}
          {page === "prompts" && <PromptStudio />}
          {page === "models" && <Models />}
          {page === "settings" && <Settings />}
          {UNAVAILABLE[page] && <Unavailable {...UNAVAILABLE[page]} />}
          </Suspense>
        </main>
      </div>
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
    </div>
  );
}
