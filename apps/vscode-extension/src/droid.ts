import * as vscode from "vscode";

type Approval = {
  id: string; run_id: string | null; kind: string; title: string; risk: string; status: string;
  details: { actions?: Record<string, any>[] }; created_at: string;
};
type AgentRun = { id: string; title: string; status: string; model: string; model_location: string; error: string | null;
  result_text: string | null; usage: Record<string, number>; session_id: string | null };
type AgentEvent = { seq: number; type: string; data: Record<string, any> };
type ApiFn = <T>(p: string, method?: string, body?: unknown) => Promise<T>;

const ACTIVE = ["starting", "running", "waiting_approval"];

class ApprovalTree implements vscode.TreeDataProvider<Approval> {
  private emitter = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.emitter.event;
  items: Approval[] = [];

  set(a: Approval[]) {
    this.items = a;
    this.emitter.fire();
  }
  getTreeItem(a: Approval): vscode.TreeItem {
    const item = new vscode.TreeItem(a.title);
    item.description = `${a.risk} risk`;
    item.tooltip = describe(a);
    item.iconPath = new vscode.ThemeIcon(a.risk === "high" ? "warning" : "question");
    item.command = { command: "localpilot.reviewApproval", title: "Review", arguments: [a] };
    return item;
  }
  getChildren(): Approval[] {
    return this.items;
  }
}

function describe(a: Approval): string {
  return (a.details.actions ?? []).map((x) => [x.file_path, x.full_command, x.risk_level_reason,
    (x.content ?? x.patch_content ?? x.new_content ?? "").slice(0, 600)].filter(Boolean).join("\n")).join("\n\n");
}

export function registerDroid(ctx: vscode.ExtensionContext, api: ApiFn, openDashboard: (hash: string) => Promise<void>,
                              config: () => vscode.WorkspaceConfiguration) {
  const tree = new ApprovalTree();
  const out = vscode.window.createOutputChannel("LocalPilot Droid");
  const notified = new Set<string>();

  const decide = async (a: Approval, decision: "approve" | "deny") => {
    try {
      await api(`/approvals/${a.id}/decide`, "POST", { decision });
      out.appendLine(`[you] ${decision === "approve" ? "approved once" : "denied"}: ${a.title}`);
    } catch (e) {
      vscode.window.showErrorMessage(`LocalPilot: ${(e as Error).message}`);
    }
    await poll();
  };

  const review = async (a: Approval) => {
    const pick = await vscode.window.showQuickPick(
      [{ label: "$(check) Approve once", id: "approve" }, { label: "$(close) Deny", id: "deny" },
       { label: "$(link-external) Open in dashboard", id: "open" }],
      { placeHolder: `${a.title} (${a.risk} risk)`, title: describe(a).split("\n")[0] || a.title },
    );
    if (pick?.id === "approve" || pick?.id === "deny") await decide(a, pick.id);
    if (pick?.id === "open") await openDashboard("#/agent");
  };

  const poll = async () => {
    try {
      const pending = await api<Approval[]>("/approvals?status=pending");
      tree.set(pending);
      vscode.commands.executeCommand("setContext", "localpilot.pendingApprovals", pending.length);
      for (const a of pending.filter((x) => !notified.has(x.id))) {
        notified.add(a.id);
        vscode.window.showWarningMessage(`Droid asks: ${a.title} (${a.risk} risk)`, "Approve once", "Deny", "Review")
          .then((c) => (c === "Approve once" ? decide(a, "approve") : c === "Deny" ? decide(a, "deny") : c ? review(a) : undefined));
      }
    } catch {
      tree.set([]);
    }
  };

  const follow = async (run: AgentRun) => {
    out.show(true);
    out.appendLine(`\n=== ${run.title} · ${run.model} (${run.model_location}) ===`);
    let after = 0;
    for (;;) {
      const chunk = await api<{ events: AgentEvent[]; next: number; active: boolean }>(`/agents/runs/${run.id}/events?after=${after}`);
      for (const e of chunk.events) {
        const d = e.data;
        if (e.type === "assistant") out.appendLine(d.text);
        else if (e.type === "tool_call") out.appendLine(`→ ${d.tool} ${String(d.input).slice(0, 200)}`);
        else if (e.type === "tool_result") out.appendLine(`← ${d.tool}${d.is_error ? " (error)" : ""}: ${String(d.content).slice(0, 400)}`);
        else if (e.type === "approval_requested") { out.appendLine(`? permission: ${d.title}`); poll(); }
        else if (e.type === "error") out.appendLine(`! ${d.message}`);
      }
      after = chunk.next;
      if (!chunk.active) break;
      await new Promise((r) => setTimeout(r, 1000));
    }
    const done = await api<AgentRun>(`/agents/runs/${run.id}`);
    const credits = done.usage?.factory_credits ? ` · ${done.usage.factory_credits} Factory credits` : "";
    out.appendLine(`=== ${done.status}${done.error ? `: ${done.error}` : ""}${credits} ===`);
    return done;
  };

  const askDroid = async (continueRun?: AgentRun) => {
    const prompt = await vscode.window.showInputBox({
      prompt: continueRun ? "Follow-up for the same Droid session" : "What should Droid do? (every change waits for your approval)",
      ignoreFocusOut: true,
    });
    if (!prompt?.trim()) return;
    const body: Record<string, unknown> = { prompt };
    if (continueRun) {
      body.continue_run_id = continueRun.id;
    } else {
      let models;
      try {
        models = await api<{ default: string; models: { id: string; name: string; location: string }[]; workspaces: string[] }>("/agents/models");
      } catch (e) {
        vscode.window.showErrorMessage(`LocalPilot: cannot list Droid models (${(e as Error).message})`);
        return;
      }
      const preferred = config().get<string>("droidModel", "") || models.default;
      const items = [...models.models].sort((a, b) => (a.id === preferred ? -1 : b.id === preferred ? 1 : a.location === "local" ? -1 : 0))
        .map((m) => ({ label: m.name, description: m.location === "local" ? "local Ollama, no credits" : "Factory cloud, uses credits", id: m.id }));
      const model = await vscode.window.showQuickPick(items, { placeHolder: "Model" });
      if (!model) return;
      const autonomy = await vscode.window.showQuickPick(
        [{ label: "Off", description: "ask before every change or command (recommended)", id: "off" },
         { label: "Low", description: "Droid may make low-risk file edits without asking", id: "low" }],
        { placeHolder: "Autonomy" });
      if (!autonomy) return;
      const ws = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
      const allowed = models.workspaces.find((w) => ws && ws.toLowerCase().startsWith(w.toLowerCase()));
      Object.assign(body, { model: model.id, autonomy: autonomy.id, cwd: allowed ? ws : models.workspaces[0] });
    }
    try {
      const run = await api<AgentRun>("/agents/runs", "POST", body);
      const done = await follow(run);
      if (done.session_id) {
        const next = await vscode.window.showInformationMessage(`Droid run ${done.status}.`, "Continue", "Open dashboard");
        if (next === "Continue") await askDroid(done);
        if (next === "Open dashboard") await openDashboard("#/agent");
      }
    } catch (e) {
      vscode.window.showErrorMessage(`LocalPilot Droid: ${(e as Error).message}`);
    }
  };

  ctx.subscriptions.push(
    out,
    vscode.window.registerTreeDataProvider("localpilot.approvals", tree),
    vscode.commands.registerCommand("localpilot.askDroid", () => askDroid()),
    vscode.commands.registerCommand("localpilot.reviewApproval", (a?: Approval) => (a ? review(a) : tree.items[0] && review(tree.items[0]))),
    vscode.commands.registerCommand("localpilot.refreshApprovals", poll),
  );
  poll();
  const timer = setInterval(poll, 4000);
  ctx.subscriptions.push({ dispose: () => clearInterval(timer) });
}
