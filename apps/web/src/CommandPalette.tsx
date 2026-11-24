import { useEffect, useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";
import { ALL_ITEMS, go } from "./nav";
import { setThemeChoice } from "./theme";

type Cmd = { id: string; label: string; hint: string; run: () => void; keywords?: string };

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);

  const cmds: Cmd[] = useMemo(() => [
    ...ALL_ITEMS.map((i) => ({ id: `go-${i.id}`, label: `Go to ${i.label}`, hint: i.available ? "Page" : "Page, not available yet",
                               keywords: i.keywords, run: () => go(i.id) })),
    { id: "new-task", label: "New Droid task", hint: "Action", keywords: "agent run", run: () => go("agents") },
    { id: "pending", label: "Review pending approvals", hint: "Action", run: () => go("decisions/approvals") },
    { id: "theme-dark", label: "Theme: dark", hint: "Appearance", run: () => setThemeChoice("dark") },
    { id: "theme-light", label: "Theme: light", hint: "Appearance", run: () => setThemeChoice("light") },
    { id: "theme-system", label: "Theme: follow system", hint: "Appearance", run: () => setThemeChoice("system") },
  ], []);

  const shown = useMemo(() => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    return cmds.filter((c) => words.every((w) => `${c.label} ${c.keywords ?? ""}`.toLowerCase().includes(w)));
  }, [q, cmds]);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) { setQ(""); setActive(0); d.showModal(); }
    if (!open && d.open) d.close();
  }, [open]);

  const run = (c?: Cmd) => { if (c) { onClose(); c.run(); } };

  return (
    <dialog ref={ref} onClose={onClose} aria-label="Command palette"
            className="m-auto mt-[15vh] w-[min(560px,92vw)] rounded-ui border border-border bg-surface p-0 text-text backdrop:bg-black/50"
            onClick={(e) => { if (e.target === ref.current) onClose(); }}>
      <div className="flex items-center gap-2 border-b border-border px-3">
        <Search aria-hidden className="h-4 w-4 text-muted" />
        <input autoFocus value={q} placeholder="Type a command or page…" aria-label="Search commands"
               className="w-full bg-transparent py-3 text-sm outline-none placeholder:text-muted"
               onChange={(e) => { setQ(e.target.value); setActive(0); }}
               onKeyDown={(e) => {
                 if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, shown.length - 1)); }
                 if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
                 if (e.key === "Enter") { e.preventDefault(); run(shown[active]); }
               }} />
      </div>
      <ul role="listbox" aria-label="Commands" className="max-h-80 overflow-auto p-1">
        {shown.length === 0 && <li className="p-3 text-sm text-muted">No matching command.</li>}
        {shown.map((c, i) => (
          <li key={c.id} role="option" aria-selected={i === active}
              onMouseEnter={() => setActive(i)} onClick={() => run(c)}
              className={`flex cursor-pointer items-center rounded-ui px-3 py-2 text-sm ${i === active ? "bg-surface-2" : ""}`}>
            <span>{c.label}</span><span className="ml-auto text-xs text-muted">{c.hint}</span>
          </li>
        ))}
      </ul>
    </dialog>
  );
}
