import * as vscode from "vscode";
import { Approval, AgentRun, AgentEvent, ApiFn, client } from "./client";
import { Preview } from "./preview";

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
  const preview = new Preview();

  const decide = async (a: Approval, decision: "approve" | "deny") => {
    try {
      await api(`/approvals/${a.id}/decide`, "POST", { decision });
      out.appendLine(`[you] ${decision === "approve" ? "approved once" : "denied"}: ${a.title}`);
    } catch (e) {
      vscode.window.showErrorMessage(`LocalPilot: ${(e as Error).message}`);
    }
    await poll();
  };

  const review = async (a: Approval, showDetails = true) => {
    a = await api<Approval>(`/approvals/${a.id}`);
    if (showDetails) await preview.details(a);
    const pick = await vscode.window.showQuickPick(
      [{ label: "$(diff) Preview proposed diff", id: "diff" },
       ...(!a.details.checkpoint_error && a.status === "pending" ? [{ label: "$(check) Approve once", id: "approve" }] : []),
       ...(a.status === "pending" ? [{ label: "$(close) Deny", id: "deny" }] : []),
       { label: "$(link-external) Open in dashboard", id: "open" }],
      { placeHolder: a.details.checkpoint_error || `${a.title} (${a.risk} risk)`, title: "Review the read-only proposal before deciding" },
    );
    if (pick?.id === "approve" || pick?.id === "deny") {
      const choice = await vscode.window.showWarningMessage(
        `${pick.id === "approve" ? "Approve once" : "Deny"}: ${a.title} (${a.risk} risk)?`,
        { modal: true }, pick.id === "approve" ? "Approve once" : "Deny");
      if (choice) await decide(a, pick.id);
    }
    if (pick?.id === "diff") { await preview.diff(a); await review(a, false); }
    if (pick?.id === "open") await openDashboard(a.run_id ? `#/agents/runs/${a.run_id}` : "#/decisions/approvals");
  };

  const poll = async () => {
    try {
      const pending = await api<Approval[]>("/approvals?status=pending");
      tree.set(pending);
      vscode.commands.executeCommand("setContext", "localpilot.pendingApprovals", pending.length);
      for (const a of pending.filter((x) => !notified.has(x.id))) {
        notified.add(a.id);
        vscode.window.showWarningMessage(`Droid asks: ${a.title} (${a.risk} risk)`, "Review")
          .then((c) => c ? review(a) : undefined);
      }
      for (const id of notified) if (!pending.some(a => a.id === id)) notified.delete(id);
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
      const allowed = models.workspaces.find((w) => ws && (ws.toLowerCase() === w.toLowerCase() ||
        ws.toLowerCase().startsWith(w.replace(/[\\/]$/, "").toLowerCase() + (ws.includes("\\") ? "\\" : "/"))));
      Object.assign(body, { model: model.id, autonomy: autonomy.id, cwd: allowed ? ws : models.workspaces[0] });
    }
    try {
      const run = await api<AgentRun>("/agents/runs", "POST", body);
      const done = await follow(run);
      if (done.session_id) {
        const next = await vscode.window.showInformationMessage(`Droid run ${done.status}.`, "Continue", "Open dashboard");
        if (next === "Continue") await askDroid(done);
        if (next === "Open dashboard") await openDashboard(`#/agents/runs/${done.id}`);
      }
    } catch (e) {
      vscode.window.showErrorMessage(`LocalPilot Droid: ${(e as Error).message}`);
    }
  };

  ctx.subscriptions.push(
    out, preview,
    vscode.window.registerTreeDataProvider("localpilot.approvals", tree),
    vscode.commands.registerCommand("localpilot.askDroidAdvanced", () => askDroid()),
    vscode.commands.registerCommand("localpilot.reviewApproval", (a?: Approval) => (a ? review(a) : tree.items[0] && review(tree.items[0]))),
    vscode.commands.registerCommand("localpilot.refreshApprovals", poll),
    vscode.commands.registerCommand("localpilot.previewApproval", (a?: Approval) => a ? preview.diff(a) : tree.items[0] && preview.diff(tree.items[0])),
    vscode.commands.registerCommand("localpilot.rollback", async () => {
      const runs = await client.agents.runs();
      const run = await vscode.window.showQuickPick(runs.map(r => ({ label: r.title, description: r.status, id: r.id })),
        { placeHolder: "Choose a run to inspect its file checkpoints" });
      if (!run) return;
      const items = (await client.agents.checkpoints(run.id)).filter(c => ["completed", "rollback_partial"].includes(c.status));
      if (!items.length) { await vscode.window.showInformationMessage("No verified file checkpoint is available for this run. Commands and unknown post-images cannot be rolled back."); return; }
      const pick = await vscode.window.showQuickPick(items.map(c => ({ label: c.files.map(f => f.path).join(", "), description: c.status, id: c.id })),
        { placeHolder: "Choose a checkpoint" });
      if (pick && await vscode.window.showWarningMessage(`Restore original files: ${pick.label}? Newer edits block rollback. Git history and index stay unchanged.`,
        { modal: true }, "Restore files")) {
        await client.agents.rollback(pick.id);
        await vscode.window.showInformationMessage("Original files restored. The outcome is recorded in History.");
      }
    }),
  );
  poll();
  const timer = setInterval(poll, 4000);
  ctx.subscriptions.push({ dispose: () => clearInterval(timer) });
}
