import {
  BookOpen, Bot, Cpu, FolderGit2, History, LayoutDashboard, ListChecks, type LucideIcon, PenLine, Scale, Server,
  Settings, Wallet,
} from "lucide-react";

export type NavItem = { id: string; label: string; icon: LucideIcon; available: boolean; keywords?: string };
export type NavGroup = { id: string; label: string; items: NavItem[] };

export const NAV: NavGroup[] = [
  { id: "workspace", label: "Workspace", items: [
    { id: "overview", label: "Overview", icon: LayoutDashboard, available: true, keywords: "home dashboard" },
    { id: "projects", label: "Projects", icon: FolderGit2, available: false },
    { id: "agents", label: "Agents", icon: Bot, available: true, keywords: "droid run task" },
    { id: "tasks", label: "Tasks", icon: ListChecks, available: false },
  ] },
  { id: "intelligence", label: "Intelligence", items: [
    { id: "prompts", label: "Prompt Studio", icon: PenLine, available: true },
    { id: "decisions", label: "Decisions", icon: Scale, available: true, keywords: "approvals approve deny permission" },
    { id: "knowledge", label: "Knowledge", icon: BookOpen, available: false },
  ] },
  { id: "operations", label: "Operations", items: [
    { id: "history", label: "History", icon: History, available: true, keywords: "audit log timeline" },
    { id: "models", label: "Models", icon: Cpu, available: true, keywords: "ollama" },
    { id: "infrastructure", label: "Infrastructure", icon: Server, available: true, keywords: "setup guide health gpu usage aws" },
    { id: "costs", label: "Costs", icon: Wallet, available: true, keywords: "credits spend usage" },
  ] },
  { id: "system", label: "System", items: [
    { id: "settings", label: "Settings", icon: Settings, available: true },
  ] },
];

export const ALL_ITEMS = NAV.flatMap((g) => g.items);

/** Old links (VS Code extension, bookmarks) keep working. */
const ALIASES: Record<string, string> = { agent: "agents", audit: "history", usage: "infrastructure", approvals: "decisions" };

export function parseHash(): { page: string; rest: string[] } {
  const parts = window.location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  let page = parts[0] ?? "overview";
  page = ALIASES[page] ?? page;
  if (page === "setup") return { page: "infrastructure", rest: ["setup", ...parts.slice(1)] };
  if (parts[0] === "usage") return { page: "infrastructure", rest: ["resources"] };
  if (!ALL_ITEMS.some((i) => i.id === page)) page = "overview";
  return { page, rest: parts.slice(1) };
}

export function go(hash: string) {
  window.location.hash = hash.startsWith("#") ? hash : `#/${hash}`;
}
