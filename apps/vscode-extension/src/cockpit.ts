import * as vscode from "vscode";
import { randomBytes } from "crypto";
import { client, AgentModel, AgentProfile, ContextItem, Project, SavedPrompt, Task, TaskInput } from "./client";

const ACTIVE = ["starting", "running", "waiting_approval", "queued"];

class Nodes implements vscode.TreeDataProvider<vscode.TreeItem> {
  private emitter = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.emitter.event;
  items: vscode.TreeItem[] = [];
  set(items: vscode.TreeItem[]) { this.items = items; this.emitter.fire(); }
  getTreeItem(item: vscode.TreeItem) { return item; }
  getChildren() { return this.items; }
  dispose() { this.emitter.dispose(); }
}

function node(label: string, description = "", command?: string, arg?: unknown, contextValue?: string) {
  const item = new vscode.TreeItem(label);
  item.description = description;
  if (command) item.command = { command, title: label, arguments: arg === undefined ? [] : [arg] };
  item.contextValue = contextValue;
  return item;
}

class Chat implements vscode.WebviewViewProvider {
  view?: vscode.WebviewView;
  constructor(private ctx: vscode.ExtensionContext, private receive: (message: any) => Promise<void>) {}
  resolveWebviewView(view: vscode.WebviewView) {
    this.view = view;
    const media = vscode.Uri.joinPath(this.ctx.extensionUri, "media");
    view.webview.options = { enableScripts: true, localResourceRoots: [media] };
    const nonce = randomBytes(16).toString("hex");
    const style = view.webview.asWebviewUri(vscode.Uri.joinPath(media, "chat.css"));
    const script = view.webview.asWebviewUri(vscode.Uri.joinPath(media, "chat.js"));
    view.webview.html = `<!doctype html><html lang="en"><head><meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${view.webview.cspSource}; script-src 'nonce-${nonce}';">
      <link rel="stylesheet" href="${style}"><title>LocalPilot Chat</title></head><body>
      <main><p id="error" role="alert" hidden></p>
      <div class="selectors"><label>Project<select id="project" aria-label="Project"></select></label>
      <label>Agent<select id="agent" aria-label="Agent"></select></label>
      <label>Model<select id="model" aria-label="Model"></select></label></div>
      <p id="estimate">Choose a model before starting.</p>
      <p id="context">No context selected. Use the Context section.</p>
      <details><summary>Task history</summary><label>Recent tasks<select id="history" aria-label="Recent tasks"></select></label>
      <button id="more" type="button">Load older tasks</button></details>
      <section aria-label="Current task"><p id="status" role="status">No active task.</p><p id="objective"></p>
      <pre id="result" aria-label="Assistant response" aria-live="polite" tabindex="0"></pre>
      <p id="tool"></p></section>
      <label for="prompt">Message</label><textarea id="prompt" rows="6" placeholder="Describe the task. Every file change or command needs approval."></textarea>
      <div class="actions"><button id="run" type="button">Run</button><button id="draft" type="button">Save task</button>
      <button id="stop" type="button" disabled>Stop</button></div>
      <details><summary>Prompts and context</summary><div class="actions">
      <button id="attach" type="button">Attach files</button><button id="prompts" type="button">Use saved prompt</button>
      <button id="savePrompt" type="button">Save prompt</button><button id="register" type="button">Register project</button></div></details>
      <div class="actions"><button id="retry" type="button">Retry task</button><button id="continue" type="button">Continue session</button>
      <button id="details" type="button">Open run details</button><button id="refresh" type="button">Refresh</button></div>
      <p class="muted">Ctrl/Cmd+Enter runs. Enter adds a line. No inference is used for navigation or saving.</p>
      </main><script nonce="${nonce}" src="${script}"></script></body></html>`;
    this.ctx.subscriptions.push(view.webview.onDidReceiveMessage(message => this.receive(message)));
  }
  send(message: unknown) { this.view?.webview.postMessage(message); }
}

export function registerCockpit(ctx: vscode.ExtensionContext, openDashboard: (hash: string) => Promise<void>) {
  const tasksTree = new Nodes(), agentsTree = new Nodes(), contextTree = new Nodes();
  tasksTree.set([node("Loading tasks…")]);
  agentsTree.set([node("Loading agents…")]);
  contextTree.set([node("Choose a project")]);
  let projects: Project[] = [], profiles: AgentProfile[] = [], models: AgentModel[] = [], tasks: Task[] = [];
  let context: ContextItem[] = [], project: Project | undefined;
  let modelId = "", agentId = "droid", selected: Task | undefined;
  let chosen = new Set<string>(), includeInstructions = false, includeArchitecture = false;
  let controller: AbortController | undefined, following: string | undefined;
  let disposed = false, loaded = false, refreshing: Promise<void> | undefined;
  const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 49);
  status.command = "localpilot.askDroid";
  const editors = new Map<string, { project?: Project; kind?: ContextItem["kind"]; title?: string; item?: ContextItem; profile?: AgentProfile }>();
  const chat = new Chat(ctx, receive);
  const report = (e: unknown) => {
    const message = e instanceof Error ? e.message : String(e);
    chat.send({ type: "error", text: message });
    vscode.window.showErrorMessage(`LocalPilot: ${message}`);
  };
  const reg = (id: string, fn: (...args: any[]) => unknown) => ctx.subscriptions.push(vscode.commands.registerCommand(id,
    async (...args: any[]) => { try { return await fn(...args); } catch (e) { report(e); } }));

  function persistContext() {
    if (project) ctx.workspaceState.update(`context:${project.id}`, { ids: [...chosen], includeInstructions, includeArchitecture });
  }
  function sendState() {
    const model = models.find(m => m.id === modelId);
    const labels = context.filter(c => chosen.has(c.id)).map(c => c.title);
    chat.send({ type: "state", projects, profiles, models, projectId: project?.id, modelId, agentId, tasks,
      context: [...(includeInstructions ? ["Project instructions"] : []), ...(includeArchitecture ? ["Architecture"] : []), ...labels] });
    status.text = selected && ACTIVE.includes(selected.status) ? `$(hubot) ${selected.status.replace("_", " ")}` : `$(hubot) ${model?.name || "Choose model"}`;
    status.tooltip = `${model?.name || "No model selected"} (${model?.location || "unknown location"})${selected ? `\nTask: ${selected.objective.slice(0, 100)}` : ""}`;
    status.show();
  }
  function renderTrees() {
    tasksTree.set(tasks.length ? tasks.map(t => {
      const item = node(t.objective.slice(0, 80), t.status.replace("_", " "), "localpilot.openTask", t,
                        ACTIVE.includes(t.status) ? "activeTask" : "task");
      item.iconPath = new vscode.ThemeIcon(t.status === "succeeded" ? "pass" : t.status === "failed" ? "error" :
        t.status === "waiting_approval" ? "question" : ACTIVE.includes(t.status) ? "sync" : "circle-outline");
      item.tooltip = `${t.objective}\n${profiles.find(p => p.id === t.agent_id)?.name || t.agent_id}\n${t.error || ""}`;
      return item;
    }) : [node(project ? "No tasks yet" : "Register or select a project", "", "localpilot.askDroid")]);
    agentsTree.set(profiles.map(p => {
      const active = tasks.filter(t => t.agent_id === p.id && ACTIVE.includes(t.status));
      const item = node(p.name, !p.enabled ? "disabled" : active.length ? `${active.length} active` : p.role,
        "localpilot.editAgent", p, "agentProfile");
      item.tooltip = `${p.adapter} adapter · ${p.role}\n${p.model || "Server default model"}\n${p.instructions}`;
      item.iconPath = new vscode.ThemeIcon(p.enabled ? "hubot" : "circle-slash");
      return item;
    }));
    const items = project ? [
      node("Project instructions", project.instructions ? "available" : "not set", "localpilot.editInstructions", "instructions"),
      node("Architecture summary", project.architecture ? "available" : "not set", "localpilot.editInstructions", "architecture"),
      ...context.map(c => {
        const item = node(c.title, c.kind === "file" ? c.path || "file" : c.kind, "localpilot.inspectContext", c, "contextItem");
        item.id = c.id;
        item.checkboxState = chosen.has(c.id) ? vscode.TreeItemCheckboxState.Checked : vscode.TreeItemCheckboxState.Unchecked;
        item.tooltip = `${c.source_hash}\nCommit: ${c.source_commit || "not recorded"}\n${c.content}`;
        return item;
      })
    ] : [node("No registered project", "", "localpilot.registerProject")];
    if (project) {
      items[0].id = "instructions"; items[1].id = "architecture";
      items[0].checkboxState = includeInstructions ? vscode.TreeItemCheckboxState.Checked : vscode.TreeItemCheckboxState.Unchecked;
      items[1].checkboxState = includeArchitecture ? vscode.TreeItemCheckboxState.Checked : vscode.TreeItemCheckboxState.Unchecked;
    }
    contextTree.set(items);
    sendState();
  }
  async function selectProject(id?: string) {
    project = projects.find(p => p.id === id);
    selected = undefined; following = undefined; controller?.abort();
    if (!project) { context = []; tasks = []; renderTrees(); return; }
    await ctx.workspaceState.update("project", project.id);
    const state = ctx.workspaceState.get<{ ids: string[]; includeInstructions: boolean; includeArchitecture: boolean }>(`context:${project.id}`);
    chosen = new Set(state?.ids || []); includeInstructions = state?.includeInstructions || false;
    includeArchitecture = state?.includeArchitecture || false;
    const idAtRequest = project.id;
    const [refs, records] = await Promise.all([client.workspace.context(idAtRequest), client.workspace.tasks(idAtRequest)]);
    if (project?.id !== idAtRequest) return;
    context = refs; tasks = records;
    renderTrees();
    chat.send({ type: "task", task: null, text: "" });
  }
  async function refresh() {
    if (refreshing) return refreshing;
    refreshing = (async () => {
      try {
        if (!loaded) {
          const catalog = await client.agents.models();
          [projects, profiles] = await Promise.all([client.workspace.projects(), client.workspace.profiles()]);
          models = catalog.models;
          modelId = vscode.workspace.getConfiguration("localpilot").get<string>("droidModel", "") || catalog.default;
          if (!models.some(m => m.id === modelId)) modelId = catalog.default;
          loaded = true;
          const remembered = ctx.workspaceState.get<string>("project");
          const folder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
          await selectProject(remembered || projects.find(p => folder?.toLowerCase() === p.root.toLowerCase())?.id);
        } else {
          profiles = await client.workspace.profiles();
          if (project) {
            const idAtRequest = project.id;
            const [p, records, refs] = await Promise.all([client.workspace.project(idAtRequest),
              client.workspace.tasks(idAtRequest), client.workspace.context(idAtRequest)]);
            if (project?.id !== idAtRequest) return;
            project = p;
            if (tasks.length > 50) {
              const old = tasks.filter(t => !records.some(r => r.id === t.id));
              tasks = [...records, ...old];
            } else tasks = records;
            context = refs;
            if (selected) {
              const selectedId = selected.id;
              const fresh = await client.workspace.task(selectedId);
              if (selected?.id === selectedId) {
                selected = fresh;
                if (fresh.run_id && fresh.run_id !== following) void follow(fresh).catch(report);
                else chat.send({ type: "task", task: fresh });
              }
            }
          }
          renderTrees();
        }
        chat.send({ type: "connected" });
      } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        for (const tree of [tasksTree, agentsTree, contextTree])
          tree.set([node("Backend unavailable, refresh to retry", message, "localpilot.refreshCockpit")]);
        chat.send({ type: "error", text: message });
        loaded = false;
      }
    })().finally(() => { refreshing = undefined; });
    return refreshing;
  }
  async function follow(t: Task) {
    controller?.abort(); controller = new AbortController();
    const signal = controller.signal;
    selected = t; following = t.run_id || undefined;
    chat.send({ type: "task", task: t, text: t.run?.result_text || "" });
    if (!t.run_id) return;
    let text = "";
    try {
      for await (const chunk of client.streamRun(t.run_id, 0, signal)) {
        if (disposed || signal.aborted) return;
        for (const event of chunk.events) {
          if (event.type === "assistant") text += `${event.data.text}\n\n`;
          if (event.type === "tool_call") chat.send({ type: "tool", text: `Using ${event.data.tool}. See run details for logs.` });
          if (event.type === "approval_requested") chat.send({ type: "tool", text: "Waiting for approval in Changes." });
        }
        chat.send({ type: "response", text: text + (chunk.partial || "") });
        if (chunk.run) { t = { ...t, run: chunk.run, status: chunk.run.status }; selected = t; chat.send({ type: "task", task: t }); }
        if (!chunk.active) {
          if (chunk.run?.result_text && !text) chat.send({ type: "response", text: chunk.run.result_text });
          return;
        }
      }
    } catch (e) {
      if (!signal.aborted) { following = undefined; throw e; }
    }
  }
  async function startTask(t: Task) {
    const fresh = await client.workspace.task(t.id);
    const preview = await client.workspace.preview(fresh.id);
    const action = preview.location === "local" ? "Start local task" : "Start cloud task";
    const choice = await vscode.window.showWarningMessage(
      `Task: ${fresh.objective.slice(0, 160)}\n${preview.model} (${preview.location}). Approximately ${preview.estimated_prompt_tokens} prompt tokens.\nSelected sources: ${preview.sources.map(s => s.title).join(", ") || "none"}.\n${preview.estimate_note}\nEvery file change or command still needs approval.`,
      { modal: true }, action);
    if (!choice) return;
    controller?.abort();
    selected = await client.workspace.start(fresh.id, fresh.revision, preview.preview_hash, preview.location !== "local");
    following = undefined;
    chat.send({ type: "task", task: selected, text: "" });
    await refresh();
  }
  async function createTask(message: any, run: boolean) {
    if (!project) throw new Error("Register or select a project first.");
    const input: TaskInput = { project_id: project.id, agent_id: agentId, model: modelId, objective: String(message.prompt || ""),
      context_ids: [...chosen], include_instructions: includeInstructions, include_architecture: includeArchitecture };
    if (run && selected?.status === "draft" && selected.project_id === input.project_id &&
        selected.objective === input.objective && selected.agent_id === input.agent_id && selected.model === input.model &&
        JSON.stringify(selected.context_ids) === JSON.stringify(input.context_ids) &&
        selected.include_instructions === input.include_instructions && selected.include_architecture === input.include_architecture) {
      await startTask(selected); return;
    }
    controller?.abort(); following = undefined;
    selected = await client.workspace.createTask(input);
    chat.send({ type: "task", task: selected, text: "" });
    if (run) await startTask(selected); else await refresh();
  }
  async function registerProject() {
    const folders = vscode.workspace.workspaceFolders || [];
    const folder = folders.length === 1 ? folders[0] : await vscode.window.showWorkspaceFolderPick();
    if (!folder) throw new Error("Open a workspace folder before registering a project.");
    const name = await vscode.window.showInputBox({ prompt: "Project name (registration does not run inference)", value: folder.name });
    if (!name) return;
    const p = await client.workspace.createProject(name, folder.uri.fsPath);
    projects = await client.workspace.projects();
    await selectProject(p.id);
  }
  async function attach() {
    if (!project) throw new Error("Select a registered project first.");
    const files = await vscode.window.showOpenDialog({ canSelectMany: true, canSelectFiles: true, canSelectFolders: false,
      defaultUri: vscode.Uri.file(project.root), title: "Attach explicit files (UTF-8, maximum 64 KiB each)" });
    for (const file of files || []) {
      const existing = context.find(c => c.kind === "file" && vscode.Uri.joinPath(vscode.Uri.file(project!.root), c.path || "").fsPath === file.fsPath);
      const item = await client.workspace.saveContext(project.id, { kind: "file", title: vscode.workspace.asRelativePath(file),
        path: file.fsPath, ...(existing ? { id: existing.id, revision: existing.revision } : {}) });
      chosen.add(item.id);
    }
    persistContext(); await refresh();
  }
  async function editor(data: { project?: Project; kind?: ContextItem["kind"]; title?: string; item?: ContextItem; profile?: AgentProfile }) {
    const content = data.profile ? JSON.stringify(data.profile, null, 2) : data.item?.content ||
      (data.kind === "instructions" ? data.project?.instructions : data.kind === "architecture" ? data.project?.architecture : "") || "";
    const doc = await vscode.workspace.openTextDocument({ language: data.profile ? "json" : "markdown", content });
    editors.set(doc.uri.toString(), data);
    await vscode.window.showTextDocument(doc);
    await vscode.window.showInformationMessage("Edit this buffer, then run LocalPilot: Save Context or Agent Editor. This saves backend records, not repository files.");
  }
  async function saveEditor() {
    const doc = vscode.window.activeTextEditor?.document;
    const data = doc && editors.get(doc.uri.toString());
    if (!doc || !data) throw new Error("Open a LocalPilot context or agent editor first.");
    if (data.profile) {
      const fields = JSON.parse(doc.getText());
      const saved = await client.workspace.saveProfile({ ...fields, id: data.profile.id, revision: data.profile.revision });
      data.profile = saved;
    } else if (data.item || data.title) {
      const saved = await client.workspace.saveContext(data.project!.id, { ...data.item, kind: data.kind!, title: data.title || data.item!.title,
        content: doc.getText() });
      data.item = saved;
    } else {
      const p = { ...data.project!, [data.kind!]: doc.getText() };
      data.project = await client.workspace.saveProject(p);
    }
    await refresh();
    await vscode.window.showInformationMessage("Saved to LocalPilot.");
  }
  async function usePrompt() {
    if (!project) throw new Error("Select a registered project first.");
    const saved = await client.workspace.prompts(project.id);
    if (!saved.length) { await vscode.window.showInformationMessage("No saved prompts for this project yet."); return; }
    const pick = await vscode.window.showQuickPick(saved.map(p => ({ label: p.name, description: `v${p.revision}`, prompt: p })),
      { placeHolder: "Choose a saved prompt" });
    if (!pick) return;
    const versions = await client.workspace.versions(pick.prompt.id);
    const version = await vscode.window.showQuickPick(versions.map(v => ({ label: `Version ${v.version}`, detail: v.content.slice(0, 120), content: v.content })),
      { placeHolder: "Choose a prompt version" });
    if (version) chat.send({ type: "prefill", text: version.content });
  }
  async function savePrompt(text: string) {
    if (!project) throw new Error("Select a registered project first.");
    const prompts = await client.workspace.prompts(project.id);
    const pick = await vscode.window.showQuickPick([{ label: "Save as new prompt", prompt: undefined as SavedPrompt | undefined },
      ...prompts.map(p => ({ label: `New version of ${p.name}`, prompt: p }))], { placeHolder: "Save a prompt without running inference" });
    if (!pick) return;
    const name = await vscode.window.showInputBox({ prompt: "Prompt name", value: pick.prompt?.name });
    if (!name) return;
    await client.workspace.savePrompt(project.id, name, text, pick.prompt?.id, pick.prompt?.revision);
    await vscode.window.showInformationMessage("Prompt saved. Previous versions are retained.");
  }
  async function moreTasks() {
    if (!project || !tasks.length) return;
    const page = await client.workspace.tasks(project.id, tasks[tasks.length - 1].id);
    tasks = [...tasks, ...page.filter(t => !tasks.some(old => old.id === t.id))];
    renderTrees();
    if (!page.length) await vscode.window.showInformationMessage("No older tasks.");
  }
  async function continueSession(text: string) {
    if (!selected?.run?.session_id) throw new Error("Select a finished run with a session first.");
    controller?.abort(); following = undefined;
    selected = await client.workspace.createTask({ project_id: selected.project_id, agent_id: selected.agent_id,
      objective: text, continue_run_id: selected.run.id, context_ids: [...chosen],
      include_instructions: includeInstructions, include_architecture: includeArchitecture });
    await startTask(selected);
  }
  async function receive(message: any) {
    try {
      switch (message?.type) {
        case "ready": await refresh(); sendState(); if (selected) chat.send({ type: "task", task: selected }); break;
        case "project": await selectProject(String(message.id)); break;
        case "model": modelId = String(message.id); sendState(); break;
        case "agent": agentId = String(message.id); sendState(); break;
        case "run": await createTask(message, true); break;
        case "draft": await createTask(message, false); break;
        case "task": { const t = await client.workspace.task(String(message.id)); await follow(t); break; }
        case "stop": if (selected) { await client.workspace.cancel(selected.id); await refresh(); } break;
        case "retry": if (selected) await startTask(selected); break;
        case "continue": await continueSession(String(message.prompt || "")); break;
        case "attach": await attach(); break;
        case "prompts": await usePrompt(); break;
        case "savePrompt": await savePrompt(String(message.prompt || "")); break;
        case "register": await registerProject(); break;
        case "details": if (selected?.run_id) await openDashboard(`#/agents/runs/${selected.run_id}`); break;
        case "refresh": await refresh(); break;
        case "more": await moreTasks(); break;
      }
    } catch (e) { report(e); }
    finally { chat.send({ type: "idle" }); }
  }

  reg("localpilot.askDroid", () => vscode.commands.executeCommand("localpilot.chat.focus"));
  reg("localpilot.refreshCockpit", refresh);
  reg("localpilot.registerProject", registerProject);
  reg("localpilot.attachFiles", attach);
  reg("localpilot.openTask", async (t: Task) => { await vscode.commands.executeCommand("localpilot.chat.focus"); await follow(await client.workspace.task(t.id)); });
  reg("localpilot.startTask", (t: Task) => startTask(t));
  reg("localpilot.cancelTask", async (t: Task) => { await client.workspace.cancel(t.id); await refresh(); });
  reg("localpilot.assignTask", async (t: Task) => {
    const pick = await vscode.window.showQuickPick(profiles.filter(p => p.enabled).map(p => ({ label: p.name, description: p.role, profile: p })),
      { placeHolder: "Assign task (does not start it)" });
    if (!pick) return;
    const fresh = await client.workspace.task(t.id);
    await client.workspace.saveTask(fresh.id, { project_id: fresh.project_id, agent_id: pick.profile.id, model: fresh.model,
      objective: fresh.objective, requirements: fresh.requirements, acceptance: fresh.acceptance, context_ids: fresh.context_ids,
      include_instructions: fresh.include_instructions, include_architecture: fresh.include_architecture, revision: fresh.revision });
    await refresh();
  });
  reg("localpilot.createAgent", async () => {
    const name = await vscode.window.showInputBox({ prompt: "Name for a new Droid agent profile" });
    if (!name) return;
    const profile = await client.workspace.saveProfile({ name, role: "Coding", instructions: "", model: null, enabled: true });
    await refresh(); await editor({ profile });
  });
  reg("localpilot.editAgent", (profile: AgentProfile) => editor({ profile }));
  reg("localpilot.toggleAgent", async (profile: AgentProfile) => { await client.workspace.saveProfile({ ...profile, enabled: !profile.enabled }); await refresh(); });
  reg("localpilot.editInstructions", (kind: "instructions" | "architecture") => project && editor({ project, kind }));
  reg("localpilot.inspectContext", async (item: ContextItem) => {
    if (item.kind === "file") {
      await vscode.window.showTextDocument(vscode.Uri.joinPath(vscode.Uri.file(project!.root), item.path!));
    } else await editor({ project, kind: item.kind, title: item.title, item });
  });
  reg("localpilot.refreshContext", async (item: ContextItem) => {
    if (project) { await client.workspace.saveContext(project.id, item); await refresh(); }
  });
  reg("localpilot.addMemory", async () => {
    if (!project) throw new Error("Select a project first.");
    const kind = await vscode.window.showQuickPick(["note", "decision"], { placeHolder: "Memory type" });
    if (!kind) return;
    const title = await vscode.window.showInputBox({ prompt: "Memory title" });
    if (title) await editor({ project, kind: kind as "note" | "decision", title });
  });
  reg("localpilot.saveContextEditor", saveEditor);
  reg("localpilot.reviewSelection", async () => {
    const active = vscode.window.activeTextEditor;
    if (!active) return;
    const text = active.document.getText(active.selection);
    await vscode.commands.executeCommand("localpilot.chat.focus");
    chat.send({ type: "prefill", text: `Review this selected code. Report bugs with evidence; do not change files.\n\n${text}` });
  });
  reg("localpilot.loadMoreTasks", moreTasks);
  const contextView = vscode.window.createTreeView("localpilot.context", { treeDataProvider: contextTree, manageCheckboxStateManually: true });
  ctx.subscriptions.push(contextView.onDidChangeCheckboxState(event => {
    for (const [item, state] of event.items) {
      const included = state === vscode.TreeItemCheckboxState.Checked;
      if (item.id === "instructions") includeInstructions = included;
      else if (item.id === "architecture") includeArchitecture = included;
      else if (item.id) included ? chosen.add(item.id) : chosen.delete(item.id);
    }
    persistContext(); renderTrees();
  }));
  ctx.subscriptions.push(status, tasksTree, agentsTree, contextTree, contextView,
    vscode.window.registerTreeDataProvider("localpilot.tasks", tasksTree),
    vscode.window.registerTreeDataProvider("localpilot.agents", agentsTree),
    vscode.window.registerWebviewViewProvider("localpilot.chat", chat, { webviewOptions: { retainContextWhenHidden: true } }),
    vscode.workspace.onDidChangeConfiguration(event => {
      if (event.affectsConfiguration("localpilot.serverUrl") || event.affectsConfiguration("localpilot.droidModel")) {
        loaded = false; controller?.abort(); void refresh();
      }
    }));
  void refresh();
  const timer = setInterval(() => { if (!disposed) void refresh(); }, 4000);
  ctx.subscriptions.push({ dispose() { disposed = true; controller?.abort(); clearInterval(timer); editors.clear(); } });
}
