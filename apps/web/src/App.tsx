import { useEffect, useState } from "react";
import Overview from "./pages/Overview";
import SetupGuide from "./pages/SetupGuide";
import Usage from "./pages/Usage";
import Audit from "./pages/Audit";
import Agent from "./pages/Agent";

const PAGES = { overview: "Overview", agent: "Droid agent", setup: "Setup guide", usage: "Usage", audit: "Audit log" } as const;
type Page = keyof typeof PAGES;

function currentPage(): Page {
  const h = window.location.hash.replace("#/", "").split("/")[0];
  return (h in PAGES ? h : "overview") as Page;
}

export default function App() {
  const [page, setPage] = useState<Page>(currentPage);
  useEffect(() => {
    const on = () => setPage(currentPage());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return (
    <div className="min-h-screen flex">
      <nav className="w-52 shrink-0 border-r border-slate-800 p-4 space-y-1">
        <div className="text-lg font-semibold mb-4">LocalPilot</div>
        {(Object.keys(PAGES) as Page[]).map((p) => (
          <a key={p} href={`#/${p}`}
             className={`block rounded px-3 py-2 text-sm ${page === p ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white"}`}>
            {PAGES[p]}
          </a>
        ))}
      </nav>
      <main className="flex-1 p-6 max-w-6xl">
        {page === "overview" && <Overview />}
        {page === "agent" && <Agent />}
        {page === "setup" && <SetupGuide />}
        {page === "usage" && <Usage />}
        {page === "audit" && <Audit />}
      </main>
    </div>
  );
}
