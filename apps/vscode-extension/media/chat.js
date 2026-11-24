(() => {
  const vscode = acquireVsCodeApi();
  const $ = id => document.getElementById(id);
  let state = {}, task = null, busy = false;
  const old = vscode.getState();
  $("prompt").value = old?.draft || "";
  function send(type, extra = {}) {
    if (["run", "draft", "retry", "continue"].includes(type)) { busy = true; buttons(); }
    vscode.postMessage({ type, prompt: $("prompt").value, ...extra });
  }
  function options(id, rows, current, empty) {
    const signature = JSON.stringify(rows);
    if ($(id).dataset.signature !== signature) {
      $(id).replaceChildren();
      const none = document.createElement("option");
      none.value = ""; none.textContent = empty; $(id).append(none);
      for (const row of rows) { const option = document.createElement("option"); option.value = row.id; option.textContent = row.label; $(id).append(option); }
      $(id).dataset.signature = signature;
    }
    $(id).value = current || "";
  }
  function estimate() {
    const model = state.models?.find(m => m.id === $("model").value);
    $("estimate").textContent = model ? `${model.name} (${model.location}). Approximately ${Math.ceil($("prompt").value.length / 4)} message tokens. System/tools, context and output are extra. ${model.location === "local" ? "No Factory credits." : "Cloud uses credits; price unknown."}` : "Choose a model before starting.";
    buttons();
  }
  function buttons() {
    const active = ["starting", "running", "waiting_approval", "queued"].includes(task?.status);
    $("run").disabled = busy || !$("prompt").value.trim() || !state.projectId || !state.modelId;
    $("draft").disabled = busy || !$("prompt").value.trim() || !state.projectId;
    $("stop").disabled = !active;
    $("retry").disabled = busy || !task || active;
    $("continue").disabled = busy || !task?.run?.session_id || active || !$("prompt").value.trim();
    $("details").disabled = !task?.run_id;
    $("savePrompt").disabled = !$("prompt").value.trim() || !state.projectId;
    $("prompts").disabled = !state.projectId;
    $("attach").disabled = !state.projectId;
    $("more").disabled = !state.tasks?.length;
  }
  window.addEventListener("message", ({ data }) => {
    if (data.type === "state") {
      state = data;
      options("project", data.projects.map(p => ({ id: p.id, label: p.name })), data.projectId, "Select project");
      options("agent", data.profiles.filter(p => p.enabled).map(p => ({ id: p.id, label: `${p.name} · ${p.role}` })), data.agentId, "Choose agent");
      options("model", data.models.map(m => ({ id: m.id, label: `${m.name} (${m.location})` })), data.modelId, "Choose model");
      options("history", data.tasks.map(t => ({ id: t.id, label: `${t.status} · ${t.objective.slice(0, 60)}` })), task?.id, "Choose recent task");
      $("context").textContent = data.context.length ? `Included: ${data.context.join(", ")}` : "No context selected. Use the Context section.";
      estimate();
    } else if (data.type === "task") {
      task = data.task;
      $("status").textContent = task ? `Task ${task.status.replaceAll("_", " ")}${task.run?.model ? ` · ${task.run.model} (${task.run.model_location})` : ""}${task.error ? `: ${task.error}` : ""}` : "No active task.";
      $("objective").textContent = task?.objective || "";
      if (data.text !== undefined) $("result").textContent = data.text;
      if (task) $("history").value = task.id;
      buttons();
    } else if (data.type === "response") $("result").textContent = data.text;
    else if (data.type === "tool") $("tool").textContent = data.text;
    else if (data.type === "prefill") { $("prompt").value = data.text; $("prompt").focus(); estimate(); }
    else if (data.type === "error") { $("error").textContent = data.text; $("error").hidden = false; }
    else if (data.type === "connected") $("error").hidden = true;
    else if (data.type === "idle") { busy = false; buttons(); }
  });
  for (const id of ["run", "draft", "stop", "retry", "continue", "attach", "prompts", "savePrompt", "register", "details", "refresh", "more"])
    $(id).addEventListener("click", () => send(id));
  for (const id of ["project", "agent", "model"]) $(id).addEventListener("change", () => send(id, { id: $(id).value }));
  $("history").addEventListener("change", () => { if ($("history").value) send("task", { id: $("history").value }); });
  $("prompt").addEventListener("input", () => { vscode.setState({ draft: $("prompt").value }); estimate(); });
  $("prompt").addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); if (!$("run").disabled) send("run"); }
  });
  buttons(); send("ready");
})();
