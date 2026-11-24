const { test } = require("node:test");
const assert = require("node:assert/strict");
const { createClient, loopbackUrl, ApiError } = require("../../../apps/vscode-extension/out/packages/api-client/src/index.js");

test("loopback origins reject remote hosts, credentials and unusual protocols", () => {
  for (const url of ["http://127.0.0.1:8765/", "http://localhost:8765", "http://[::1]:8765"])
    assert.ok(loopbackUrl(url));
  for (const url of ["https://example.com", "file:///tmp", "http://user:pass@localhost:8765", "http://localhost:8765/path", "http://localhost:8765?q=1"])
    assert.throws(() => loopbackUrl(url));
});

test("concurrent reads share a promise; writes remain independent and identify the surface", async () => {
  const calls = [];
  const c = createClient({ baseUrl: "http://127.0.0.1:8765", surface: "vscode",
    fetch: async (url, init) => { calls.push({ url, init }); return Response.json([]); } });
  await Promise.all([c.api.runbooks(), c.api.runbooks()]);
  assert.equal(calls.length, 1);
  await Promise.all([c.workspace.createProject("A", "E:/a"), c.workspace.createProject("B", "E:/b")]);
  assert.equal(calls.length, 3);
  assert.equal(calls[1].init.headers["x-localpilot-surface"], "vscode");
  assert.equal(calls[1].init.headers["x-localpilot-client"], "1");
});

test("failed reads can retry and structured validation errors remain readable", async () => {
  let count = 0;
  const c = createClient({ fetch: async () => ++count === 1 ? Response.json({ detail: [{ msg: "Missing project" }] }, { status: 422 }) : Response.json([]) });
  await assert.rejects(c.workspace.projects(), e => e instanceof ApiError && e.status === 422 && e.message === "Missing project");
  assert.deepEqual(await c.workspace.projects(), []);
});

test("health cache is scoped to the configured origin", async () => {
  let origin = "http://127.0.0.1:8765", count = 0;
  const c = createClient({ baseUrl: () => origin, fetch: async () => { count++; return Response.json({ status: "ok", checks: [] }); } });
  await c.api.health(); await c.api.health();
  assert.equal(count, 1);
  origin = "http://127.0.0.1:8767";
  await c.api.health();
  assert.equal(count, 2);
});

test("SSE preserves split UTF-8 and CRLF boundaries and consumes the final run", async () => {
  const wire = ': keep-alive\r\n\r\ndata: {"events":[],"next":1,"partial":"✓","active":true}\r\n\r\nevent: end\r\ndata: {"next":1,"run":{"id":"r","status":"succeeded"}}\r\n\r\n';
  const bytes = new TextEncoder().encode(wire);
  const body = new ReadableStream({ start(controller) { for (const byte of bytes) controller.enqueue(Uint8Array.of(byte)); controller.close(); } });
  const c = createClient({ fetch: async () => new Response(body, { headers: { "content-type": "text/event-stream" } }) });
  const rows = [];
  for await (const row of c.streamRun("r", 0, new AbortController().signal)) rows.push(row);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].partial, "✓");
  assert.equal(rows[1].active, false);
  assert.equal(rows[1].run.status, "succeeded");
});

test("task start binds explicit consent to the reviewed preview", async () => {
  let body;
  const c = createClient({ fetch: async (_, init) => { body = JSON.parse(init.body); return Response.json({ status: "queued" }); } });
  await c.workspace.start("t", 2, "hash", false);
  assert.deepEqual(body, { revision: 2, preview_hash: "hash", approved: true, allow_cloud: false });
  assert.equal(c.api.auditExportUrl("json", { q: "a&b" }), "/api/v1/audit/export?q=a%26b&format=json");
});
