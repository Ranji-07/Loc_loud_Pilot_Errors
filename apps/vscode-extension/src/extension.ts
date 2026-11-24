import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";
import { registerDroid } from "./droid";

type Check = { name: string; status: string; detail: string };
type Health = { version: string; status: string; checks: Check[] };
type Runbook = { id: string; title: string; summary: string; steps: number };
type Usage = { id: number; alerts: { level: string; text: string }[]; local?: { cpu_percent: number; ram_used_percent: number } };

const ICONS: Record<string, string> = {
  ok: "pass", warn: "warning", error: "error", info: "info", not_configured: "circle-outline",
};

function config() {
  return vscode.workspace.getConfiguration("localpilot");
}

function serverUrl(): string {
  const url = config().get<string>("serverUrl", "http://127.0.0.1:8765").replace(/\/+$/, "");
  const host = new URL(url).hostname;
  if (!["127.0.0.1", "localhost", "[::1]"].includes(host)) {
    throw new Error("localpilot.serverUrl must point to a loopback address");
  }
  return url;
}

async function api<T>(p: string, method = "GET", body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "x-localpilot-client": "1", "x-localpilot-surface": "vscode" };
  if (body !== undefined) headers["content-type"] = "application/json";
  const r = await fetch(`${serverUrl()}/api/v1${p}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(method === "GET" ? 15000 : 120000),
  });
  if (!r.ok) {
    const data = (await r.json().catch(() => ({}))) as { error?: string };
    throw new Error(data.error ?? `${r.status} ${r.statusText}`);
  }
  return (await r.json()) as T;
}

class HealthTree implements vscode.TreeDataProvider<Check> {
  private emitter = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.emitter.event;
  health: Health | null = null;

  set(h: Health | null) {
    this.health = h;
    this.emitter.fire();
  }
  getTreeItem(c: Check): vscode.TreeItem {
    const item = new vscode.TreeItem(c.name.replace("_", " "));
    item.description = c.status.replace("_", " ");
    item.tooltip = c.detail;
    item.iconPath = new vscode.ThemeIcon(ICONS[c.status] ?? "circle-outline");
    return item;
  }
  getChildren(): Check[] {
    return this.health?.checks ?? [];
  }
}

class GuideTree implements vscode.TreeDataProvider<Runbook> {
  private emitter = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.emitter.event;
  books: Runbook[] = [];

  set(b: Runbook[]) {
    this.books = b;
    this.emitter.fire();
  }
  getTreeItem(b: Runbook): vscode.TreeItem {
    const item = new vscode.TreeItem(b.title);
    item.description = `${b.steps} steps`;
    item.tooltip = b.summary;
    item.iconPath = new vscode.ThemeIcon("checklist");
    item.command = { command: "localpilot.openGuide", title: "Open guide", arguments: [b.id] };
    return item;
  }
  getChildren(): Runbook[] {
    return this.books;
  }
}

async function openInVsCode(url: string) {
  try {
    await vscode.commands.executeCommand("simpleBrowser.show", url);
  } catch {
    await vscode.env.openExternal(vscode.Uri.parse(url));
  }
}

function findRepo(): string | undefined {
  const configured = config().get<string>("repoPath", "");
  const candidates = [configured, ...(vscode.workspace.workspaceFolders ?? []).map((f) => f.uri.fsPath)].filter(Boolean);
  return candidates.find((c) => fs.existsSync(path.join(c, "backend", "localpilot", "main.py")));
}

export function activate(ctx: vscode.ExtensionContext) {
  const healthTree = new HealthTree();
  const guideTree = new GuideTree();
  const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
  status.command = "localpilot.showHealth";
  status.show();
  const output = vscode.window.createOutputChannel("LocalPilot");

  const refresh = async () => {
    try {
      const [h, books] = await Promise.all([api<Health>("/health"), api<Runbook[]>("/runbooks")]);
      healthTree.set(h);
      guideTree.set(books);
      const icon = h.status === "ok" ? "$(pass)" : h.status === "warn" ? "$(warning)" : "$(error)";
      status.text = `${icon} LocalPilot`;
      const issues = h.checks.filter((c) => c.status === "warn" || c.status === "error");
      status.tooltip = issues.length ? issues.map((c) => `${c.name}: ${c.detail}`).join("\n") : "All checks OK";
      status.backgroundColor = h.status === "error" ? new vscode.ThemeColor("statusBarItem.errorBackground") : undefined;
    } catch (e) {
      healthTree.set(null);
      guideTree.set([]);
      status.text = "$(debug-disconnect) LocalPilot offline";
      status.tooltip = `Backend not reachable (${(e as Error).message}). Click for details.`;
      status.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
    }
  };

  const reg = (id: string, fn: (...a: any[]) => unknown) => ctx.subscriptions.push(vscode.commands.registerCommand(id, fn));

  reg("localpilot.refresh", refresh);
  reg("localpilot.openDashboard", () => openInVsCode(`${serverUrl()}/`));
  reg("localpilot.openGuide", async (id?: string) => {
    if (!id) {
      const pick = await vscode.window.showQuickPick(
        guideTree.books.map((b) => ({ label: b.title, detail: b.summary, id: b.id })),
        { placeHolder: "Choose a setup guide" },
      );
      id = pick?.id;
    }
    if (id) await openInVsCode(`${serverUrl()}/#/setup/${id}`);
  });
  reg("localpilot.showHealth", async () => {
    await refresh();
    if (!healthTree.health) {
      const choice = await vscode.window.showWarningMessage("LocalPilot backend is not reachable.", "Start backend");
      if (choice) await vscode.commands.executeCommand("localpilot.startBackend");
      return;
    }
    await vscode.window.showQuickPick(
      healthTree.health.checks.map((c) => ({ label: `$(${ICONS[c.status] ?? "circle-outline"}) ${c.name}`, description: c.status, detail: c.detail })),
      { placeHolder: `LocalPilot ${healthTree.health.version}: overall ${healthTree.health.status}` },
    );
  });
  reg("localpilot.showUsage", async () => {
    await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: "LocalPilot: measuring usage" }, async (p) => {
      try {
        const u = await api<Usage>("/usage");
        output.clear();
        output.appendLine(`CPU ${u.local?.cpu_percent}%  RAM ${u.local?.ram_used_percent}%`);
        u.alerts.forEach((a) => output.appendLine(`[${a.level}] ${a.text}`));
        p.report({ message: "asking the small local model for a summary" });
        const s = await api<{ text: string | null; error?: string; model: string | null; source: string }>(`/usage/${u.id}/summary`, "POST");
        output.appendLine("");
        output.appendLine(`Summary (${s.source}${s.model ? `, ${s.model}` : ""}):`);
        output.appendLine(s.text ?? s.error ?? "");
        output.show(true);
      } catch (e) {
        vscode.window.showErrorMessage(`LocalPilot usage failed: ${(e as Error).message}`);
      }
    });
  });
  reg("localpilot.startBackend", () => {
    const repo = findRepo();
    if (!repo) {
      vscode.window.showErrorMessage("Set localpilot.repoPath to the LocalPilot repository folder.");
      return;
    }
    const py = path.join(repo, "backend", ".venv", process.platform === "win32" ? "Scripts\\python.exe" : "bin/python");
    const term = vscode.window.createTerminal({ name: "LocalPilot backend", cwd: path.join(repo, "backend") });
    term.sendText(`& "${py}" -m localpilot`);
    term.show(true);
    setTimeout(refresh, 5000);
  });

  ctx.subscriptions.push(
    status, output,
    vscode.window.registerTreeDataProvider("localpilot.health", healthTree),
    vscode.window.registerTreeDataProvider("localpilot.guides", guideTree),
  );
  registerDroid(ctx, api, (hash) => openInVsCode(`${serverUrl()}/${hash}`), config);
  refresh();
  const timer = setInterval(refresh, Math.max(5, config().get<number>("pollSeconds", 30)) * 1000);
  ctx.subscriptions.push({ dispose: () => clearInterval(timer) });
}

export function deactivate() {}
