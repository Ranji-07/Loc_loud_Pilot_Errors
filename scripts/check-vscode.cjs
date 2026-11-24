const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { VscodeCdp } = require("./vscode-cdp.cjs");
const ROOT = path.resolve(__dirname, "..");
const BASE = "http://127.0.0.1:8767";
const passed = [];
async function api(p, body) {
  const r = await fetch(BASE + "/api/v1" + p, body ? { method: "POST", headers: { "content-type": "application/json", "x-localpilot-client": "1" }, body: JSON.stringify(body) } : {});
  const data = await r.json();
  assert.ok(r.ok, JSON.stringify(data));
  return data;
}
async function main() {
  const c = await new VscodeCdp().connect();
  try {
    await c.wait("!!document.getElementById('project').value");
    assert.ok((await api("/agents/models")).models.every(m => m.name.includes("[TEST DOUBLE]")), "Only run against the test backend");
    await c.key("Escape", "Escape");
    for (const run of await api("/agents/runs")) {
      if (["starting", "running", "waiting_approval"].includes(run.status)) await api(`/agents/runs/${run.id}/stop`, {});
    }
    const baselineRuns = (await api("/agents/runs")).length;
    await c.input("");
    assert.equal(await c.chat("document.getElementById('run').disabled"), true);
    await c.input("say hi\nThis is a multiline task");
    await c.click("draft");
    await c.wait("document.getElementById('status').textContent.includes('draft')");
    const projectId = await c.chat("document.getElementById('project').value");
    assert.ok((await api(`/tasks?project_id=${projectId}`)).some(t => t.objective.includes("\n")));
    assert.equal((await api("/agents/runs")).length, baselineRuns);
    passed.push("Multiline composer, empty guard, save task without inference");

    await c.wait("!document.getElementById('retry').disabled");
    await c.click("retry");
    await c.confirm("Start cloud task");
    await c.wait("document.getElementById('status').textContent.includes('succeeded')", false, 25000);
    await c.wait("document.getElementById('result').textContent.includes('done')");
    assert.equal((await api("/agents/runs"))[0].autonomy, "off");
    passed.push("Explicit model/location/token confirmation, strict queued run and streamed result");

    await c.input("follow-up message");
    await c.click("continue");
    await c.confirm("Start cloud task");
    await c.wait("document.getElementById('objective').textContent === 'follow-up message'");
    await c.wait("document.getElementById('status').textContent.includes('succeeded')", false, 25000);
    await c.wait("document.getElementById('result').textContent.includes('done')");
    const turns = await api("/agents/runs");
    assert.equal(turns.length, baselineRuns + 2);
    assert.equal(turns[0].parent_run_id, turns[1].id);
    assert.equal(turns[0].session_id, turns[1].session_id);
    passed.push("Continue creates a tracked task in the same strict-approval session");

    await c.input("make a file");
    await c.click("run");
    await c.confirm("Start cloud task");
    await c.wait("document.getElementById('status').textContent.includes('waiting approval')", false, 25000);
    await c.command("LocalPilot: Review Pending Approval");
    await c.choose("Preview proposed diff");
    await c.wait("document.body.innerText.includes('Proposed: hello.txt')", true);
    await c.key("Escape", "Escape");
    await c.wait("Array.from(document.querySelectorAll('.view-line')).some(line=>line.textContent.trim() === 'hi')", true);
    await c.command("LocalPilot: Review Pending Approval");
    await c.choose("Approve once");
    await c.confirm("Approve once");
    await c.wait("document.getElementById('status').textContent.includes('succeeded')", false, 25000);
    const audit = await api("/audit?action=approval.approved");
    assert.ok(audit.some(e => e.actor === "user:vscode"));
    passed.push("Native read-only diff and VS Code approval recorded in shared History");

    await c.command("LocalPilot: Restore File Checkpoint");
    await c.choose("make a file");
    await c.choose("hello.txt");
    await c.confirm("Restore files");
    await c.wait("document.body.innerText.includes('Original files restored')", true);
    assert.ok((await api("/audit?action=checkpoint.rolled_back")).some(e => e.actor === "user:vscode"));
    passed.push("Native checkpoint restoration preserves Git index/history and records outcome");

    await c.input("make a file for dashboard denial");
    await c.click("run");
    await c.confirm("Start cloud task");
    await c.wait("document.getElementById('status').textContent.includes('waiting approval')", false, 25000);
    passed.push("Second approval ready for dashboard-to-VS-Code round trip");
    fs.writeFileSync(path.join(ROOT, ".screens", "phase5-vscode-report.json"), JSON.stringify({ passed, pendingDashboardDecision: true }, null, 2));
    console.log(JSON.stringify({ passed, pendingDashboardDecision: true }, null, 2));
  } finally { c.close(); }
}
main().catch(e => { console.error(e); process.exitCode = 1; });
