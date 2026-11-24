import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type Policy, type Run, type RunbookSummary, type StepView } from "../api";
import { Badge, ErrorBox } from "../ui";

function selectedFromHash(): string | null {
  return window.location.hash.split("/")[2] ?? null;
}

export default function SetupGuide() {
  const [books, setBooks] = useState<RunbookSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(selectedFromHash);
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.runbooks().then((b) => {
      setBooks(b);
      setSelected((s) => s ?? b[0]?.id ?? null);
    }).catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    window.location.hash = `#/setup/${selected}`;
    setRun(null);
    api.runbook(selected).then((rb) => setRun(rb.runs[0] ?? null)).catch((e) => setError((e as Error).message));
  }, [selected]);

  const refresh = useCallback(async () => {
    if (run) setRun(await api.run(run.id));
  }, [run]);

  const start = async () => {
    if (!selected) return;
    try {
      setRun(await api.startRun(selected));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const book = books.find((b) => b.id === selected);
  const done = run?.steps.filter((s) => s.status === "succeeded" || s.status === "skipped").length ?? 0;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Setup guide</h1>
      <p className="text-sm text-muted">
        Each step shows the exact command first. Nothing runs until you press <b>Execute</b>. You can edit a command
        before running it, stop a running step, skip a step, or verify the result.
      </p>
      <ErrorBox error={error} />
      <div className="flex flex-wrap gap-2">
        {books.map((b) => (
          <button key={b.id} onClick={() => setSelected(b.id)}
                  className={b.id === selected ? "btn-primary" : "btn-ghost"}>{b.title}</button>
        ))}
      </div>
      {book && (
        <div className="card flex items-center gap-4">
          <div className="flex-1">
            <div className="font-medium">{book.title}</div>
            <div className="text-sm text-muted">{book.summary}</div>
          </div>
          {run && <div className="text-sm text-text">{done} / {run.steps.length} done</div>}
          {run && <Badge value={run.status === "completed" ? "succeeded" : "info"} label={run.status} />}
          <button className={run ? "btn-ghost" : "btn-primary"} onClick={start}>{run ? "Start over" : "Start guide"}</button>
        </div>
      )}
      {run && (
        <ol className="space-y-3">
          {run.steps.map((s, i) => (
            <StepCard key={`${run.id}-${s.id}`} index={i + 1} runId={run.id} step={s} onChange={setRun} onRefresh={refresh} />
          ))}
        </ol>
      )}
    </div>
  );
}

function StepCard({ index, runId, step, onChange, onRefresh }: {
  index: number; runId: string; step: StepView; onChange: (r: Run) => void; onRefresh: () => Promise<void>;
}) {
  const [command, setCommand] = useState(step.executed_command ?? step.command);
  const [policy, setPolicy] = useState<Policy>(step.policy);
  const [confirmHigh, setConfirmHigh] = useState(false);
  const [lines, setLines] = useState<string[]>([]);
  const [showOutput, setShowOutput] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verify, setVerify] = useState<{ passed: boolean; output: string } | null>(null);
  const source = useRef<EventSource | null>(null);
  const edited = command.trim() !== step.command.trim();
  const running = step.status === "running";

  useEffect(() => {
    if (!edited) {
      setPolicy(step.policy);
      return;
    }
    const t = setTimeout(() => {
      api.evaluate(runId, step.id, command).then(setPolicy).catch(() => undefined);
    }, 300);
    return () => clearTimeout(t);
  }, [command, edited, runId, step.id, step.policy]);

  const follow = useCallback(() => {
    source.current?.close();
    setLines([]);
    setShowOutput(true);
    const es = new EventSource(`/api/v1/runs/${runId}/steps/${step.id}/stream`);
    source.current = es;
    es.onmessage = (ev) => {
      const data = JSON.parse(ev.data) as { lines: string[] };
      setLines((prev) => [...prev, ...data.lines].slice(-3000));
    };
    es.addEventListener("end", () => {
      es.close();
      source.current = null;
      onRefresh();
    });
    es.onerror = () => {
      es.close();
      source.current = null;
    };
  }, [runId, step.id, onRefresh]);

  useEffect(() => {
    if (running && !source.current) follow();
  }, [running, follow]);
  useEffect(() => () => source.current?.close(), []);

  const act = async (fn: () => Promise<Run | void>) => {
    setBusy(true);
    setError(null);
    try {
      const r = await fn();
      if (r) onChange(r);
    } catch (e) {
      const err = e as ApiError;
      const reasons = (err.detail as Policy | undefined)?.reasons;
      setError(reasons?.length ? `${err.message}: ${reasons.join("; ")}` : err.message);
    } finally {
      setBusy(false);
    }
  };

  const execute = () => act(async () => {
    setVerify(null);
    const r = await api.execute(runId, step.id, edited ? command : null, confirmHigh);
    follow();
    return r;
  });

  const loadOutput = async () => {
    if (showOutput) return setShowOutput(false);
    const out = await api.output(runId, step.id);
    setLines(out.lines);
    setShowOutput(true);
  };

  const high = policy.risk === "high";
  return (
    <li className="card space-y-3" data-step={step.id}>
      <div className="flex items-center gap-2">
        <span className="text-muted text-sm w-6">{index}.</span>
        <span className="font-medium">{step.title}</span>
        {step.optional && <Badge value="info" label="optional" />}
        <Badge value={policy.risk} label={`${policy.risk} risk`} />
        <span className="ml-auto"><Badge value={step.status} /></span>
        {step.exit_code !== null && <span className="text-xs text-muted">exit {step.exit_code}</span>}
      </div>
      <p className="text-sm text-text whitespace-pre-line">{step.explain}</p>
      <div>
        <div className="flex items-center gap-2 text-xs text-muted mb-1">
          <span>Command {edited && <span className="text-text">(modified)</span>}</span>
          {edited && <button className="underline" onClick={() => setCommand(step.command)}>reset</button>}
        </div>
        <textarea value={command} onChange={(e) => setCommand(e.target.value)} disabled={running} spellCheck={false}
                  rows={Math.min(6, command.split("\n").length + (command.length > 110 ? 1 : 0))}
                  className="w-full rounded bg-bg border border-border-strong p-2 font-mono text-xs text-text" />
        {!policy.allowed && (
          <div className="mt-1 text-xs text-danger">Policy blocks this command: {policy.reasons.join("; ")}</div>
        )}
        {step.expected && <div className="mt-1 text-xs text-muted">Expected: {step.expected}</div>}
        {step.rollback && <div className="text-xs text-muted">Undo: <code>{step.rollback}</code></div>}
      </div>
      {high && !running && (
        <label className="flex items-center gap-2 text-sm text-danger">
          <input type="checkbox" checked={confirmHigh} onChange={(e) => setConfirmHigh(e.target.checked)} />
          I understand this is high risk (it can create, change or bill cloud resources).
        </label>
      )}
      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" disabled={busy || running || !policy.allowed || (high && !confirmHigh)} onClick={execute}>
          {step.status === "pending" ? "Execute" : "Run again"}
        </button>
        <button className="btn-danger" disabled={busy || !running} onClick={() => act(() => api.stop(runId, step.id))}>Stop</button>
        <button className="btn-ghost" disabled={busy || running} onClick={() => act(() => api.skip(runId, step.id))}>Skip</button>
        {step.check && (
          <button className="btn-ghost" disabled={busy || running}
                  onClick={() => act(async () => setVerify(await api.check(runId, step.id)))}>Verify</button>
        )}
        {step.status !== "pending" && !running && (
          <button className="btn-ghost" onClick={loadOutput}>{showOutput ? "Hide output" : "Show output"}</button>
        )}
      </div>
      <ErrorBox error={error} />
      {verify && (
        <div className={`rounded p-2 text-xs ${verify.passed ? "bg-success-soft text-text" : "bg-danger-soft text-danger"}`}>
          Verification {verify.passed ? "passed" : "failed"}
          {verify.output && <pre className="mt-1 whitespace-pre-wrap">{verify.output}</pre>}
        </div>
      )}
      {showOutput && (
        <pre className="max-h-72 overflow-auto rounded bg-black p-2 font-mono text-xs text-text whitespace-pre-wrap">
          {lines.length ? lines.join("\n") : running ? "Waiting for output…" : "(no output)"}
        </pre>
      )}
    </li>
  );
}
