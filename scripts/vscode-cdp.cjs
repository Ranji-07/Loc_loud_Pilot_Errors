const assert = require("node:assert/strict");

class VscodeCdp {
  async connect(port = 9223) {
    const version = await fetch(`http://127.0.0.1:${port}/json/version`).then(r => r.json());
    this.socket = new WebSocket(version.webSocketDebuggerUrl);
    this.sequence = 0; this.pending = new Map(); this.contexts = [];
    await new Promise((resolve, reject) => { this.socket.addEventListener("open", resolve); this.socket.addEventListener("error", reject); });
    this.socket.addEventListener("message", ({ data }) => {
      const packet = JSON.parse(data);
      if (packet.method === "Runtime.executionContextCreated") this.contexts.push({ ...packet.params.context, session: packet.sessionId });
      if (packet.id) {
        const waiter = this.pending.get(packet.id);
        if (waiter) { this.pending.delete(packet.id); clearTimeout(waiter.timer); packet.error ? waiter.reject(new Error(packet.error.message)) : waiter.resolve(packet.result); }
      }
    });
    const { targetInfos } = await this.send("Target.getTargets");
    const main = targetInfos.find(t => t.type === "page" && t.title.includes("LocalPilot Phase 5 Test"));
    assert.ok(main, "Only connect to the isolated LocalPilot test window");
    const frame = targetInfos.find(t => t.type === "iframe" && t.url.includes("extensionId=localpilot.localpilot"));
    assert.ok(frame, "Open LocalPilot Chat before running this check");
    this.main = (await this.send("Target.attachToTarget", { targetId: main.targetId, flatten: true })).sessionId;
    this.frame = (await this.send("Target.attachToTarget", { targetId: frame.targetId, flatten: true })).sessionId;
    await this.send("Runtime.enable", {}, this.main);
    await this.send("Runtime.enable", {}, this.frame);
    for (const ctx of this.contexts.filter(c => c.session === this.frame && c.auxData?.isDefault)) {
      if (await this.evaluate("!!document.getElementById('prompt')", this.frame, ctx.id)) { this.chatContext = ctx.id; break; }
    }
    assert.ok(this.chatContext, "Chat execution context must be rendered");
    return this;
  }
  send(method, params = {}, sessionId) {
    const id = ++this.sequence;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, 15000);
      this.pending.set(id, { resolve, reject, timer });
      this.socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
    });
  }
  async evaluate(expression, session = this.frame, contextId = this.chatContext) {
    const r = await this.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true,
      ...(contextId ? { contextId } : {}) }, session);
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ": " + (r.exceptionDetails.exception?.description || ""));
    return r.result.value;
  }
  mainEval(code) { return this.evaluate(code, this.main, null); }
  chat(code) { return this.evaluate(code); }
  async wait(code, native = false, timeout = 15000) {
    const deadline = Date.now() + timeout;
    for (;;) {
      if (await (native ? this.mainEval(code) : this.chat(code))) return;
      if (Date.now() >= deadline) throw new Error(`UI wait failed: ${code}`);
      await new Promise(resolve => setTimeout(resolve, 80));
    }
  }
  async input(text) {
    await this.chat(`(() => { const p=document.getElementById("prompt"); p.value=${JSON.stringify(text)}; p.dispatchEvent(new Event("input",{bubbles:true})); })()`);
  }
  click(id) { return this.chat(`document.getElementById(${JSON.stringify(id)}).click()`); }
  async key(key, code, modifiers = 0) {
    const virtual = key.length === 1 ? key.toUpperCase().charCodeAt(0) : { Enter: 13, Escape: 27, ArrowDown: 40, Tab: 9 }[key] || 0;
    await this.send("Input.dispatchKeyEvent", { type: "rawKeyDown", key, code, modifiers, windowsVirtualKeyCode: virtual }, this.main);
    await this.send("Input.dispatchKeyEvent", { type: "keyUp", key, code, modifiers: 0, windowsVirtualKeyCode: virtual }, this.main);
  }
  async command(name) {
    await this.key("P", "KeyP", 10);
    await this.wait("!!document.querySelector('.quick-input-widget input')", true);
    await this.key("a", "KeyA", 2);
    await this.send("Input.insertText", { text: `>${name}` }, this.main);
    await this.wait(`Array.from(document.querySelectorAll('.quick-input-widget .monaco-list-row')).some(r=>r.textContent.includes(${JSON.stringify(name)}))`, true);
    await this.key("Enter", "Enter");
  }
  async choose(text) {
    await this.wait(`Array.from(document.querySelectorAll('.quick-input-widget .monaco-list-row')).some(r=>r.textContent.includes(${JSON.stringify(text)}))`, true);
    await this.key("a", "KeyA", 2);
    await this.send("Input.insertText", { text }, this.main);
    await this.wait(`document.querySelector('.quick-input-widget input').value === ${JSON.stringify(text)} &&
      Array.from(document.querySelectorAll('.quick-input-widget .monaco-list-row')).some(r=>r.offsetHeight && r.textContent.includes(${JSON.stringify(text)}))`, true);
    await this.key("Enter", "Enter");
  }
  async confirm(text) {
    await this.wait(`Array.from(document.querySelectorAll('.monaco-dialog-box .monaco-button')).some(b=>b.textContent === ${JSON.stringify(text)})`, true);
    await this.mainEval(`Array.from(document.querySelectorAll('.monaco-dialog-box .monaco-button')).find(b=>b.textContent === ${JSON.stringify(text)}).click()`);
  }
  close() { this.socket.close(); }
}

module.exports = { VscodeCdp };
if (require.main === module) {
  (async () => {
    const c = await new VscodeCdp().connect();
    try { console.log(await c.chat("document.body.innerText")); } finally { c.close(); }
  })().catch(e => { console.error(e); process.exitCode = 1; });
}
