import * as vscode from "vscode";
import { Approval } from "./client";

export class Preview implements vscode.TextDocumentContentProvider, vscode.Disposable {
  private texts = new Map<string, string>();
  private serial = 0;
  private registration = vscode.workspace.registerTextDocumentContentProvider("localpilot-preview", this);
  provideTextDocumentContent(uri: vscode.Uri) { return this.texts.get(uri.toString()) || ""; }
  dispose() { this.registration.dispose(); this.texts.clear(); }
  private uri(name: string, text: string) {
    const uri = vscode.Uri.from({ scheme: "localpilot-preview", path: `/${++this.serial}/${name}` });
    this.texts.set(uri.toString(), text);
    return uri;
  }
  async details(a: Approval) {
    const uri = this.uri("proposal.json", JSON.stringify({ title: a.title, risk: a.risk, status: a.status, ...a.details }, null, 2));
    await vscode.window.showTextDocument(uri, { preview: true, preserveFocus: true });
  }
  async diff(a: Approval) {
    const choices: { label: string; old: string; next: string }[] = [];
    for (const action of a.details.actions || []) {
      for (const file of action.files?.length ? action.files : [action]) {
        if (action.preview_truncated || file.preview_truncated) continue;
        const before = action.type === "CreateFile" || file.operation === "create" ? "" : file.old_content;
        const after = file.operation === "delete" ? "" : action.type === "CreateFile" ? action.content : file.new_content;
        if (typeof before === "string" && typeof after === "string")
          choices.push({ label: file.file_path || action.file_name || "Proposed file", old: before, next: after });
      }
    }
    const pick = choices.length === 1 ? choices[0] : choices.length ? await vscode.window.showQuickPick(choices, { placeHolder: "Choose proposed file" }) : undefined;
    if (!pick) {
      if (!choices.length) {
        await this.details(a);
        await vscode.window.showInformationMessage("Full before/after contents are unavailable. The supplied proposal is open; no diff was invented.");
      }
      return;
    }
    const name = pick.label.replace(/\\/g, "/").split("/").pop() || "file.txt";
    await vscode.commands.executeCommand("vscode.diff", this.uri(`before-${name}`, pick.old),
      this.uri(`proposed-${name}`, pick.next), `Proposed: ${name}`, { preview: true });
  }
}
