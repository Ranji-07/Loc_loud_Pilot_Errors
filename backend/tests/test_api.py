from __future__ import annotations

import time

from tests.conftest import HEADERS, step_of, wait_done


def start(client) -> dict:
    r = client.post("/api/v1/runbooks/test-book/runs", headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


def test_healthz_and_runbooks(client):
    assert client.get("/healthz").json()["status"] == "ok"
    books = client.get("/api/v1/runbooks").json()
    assert [b["id"] for b in books] == ["test-book"]


def test_mutations_require_client_header(client):
    r = client.post("/api/v1/runbooks/test-book/runs")
    assert r.status_code == 403


def test_foreign_origin_rejected(client):
    r = client.post("/api/v1/runbooks/test-book/runs", headers={**HEADERS, "origin": "https://evil.example"})
    assert r.status_code == 403


def test_foreign_host_rejected(client):
    r = client.get("/api/v1/runbooks", headers={"host": "evil.example:8765"})
    assert r.status_code == 421


def test_execute_requires_approval(client):
    run = start(client)
    r = client.post(f"/api/v1/runs/{run['id']}/steps/hello/execute", json={"approved": False}, headers=HEADERS)
    assert r.status_code == 400


def test_execute_success_and_output(client):
    run = start(client)
    r = client.post(f"/api/v1/runs/{run['id']}/steps/hello/execute", json={"approved": True}, headers=HEADERS)
    assert r.status_code == 200, r.text
    out = wait_done(client, run["id"], "hello")
    assert "hello from step" in "\n".join(out["lines"])
    st = step_of(client.get(f"/api/v1/runs/{run['id']}").json(), "hello")
    assert st["status"] == "succeeded" and st["exit_code"] == 0 and not st["modified"]


def test_failed_step(client):
    run = start(client)
    client.post(f"/api/v1/runs/{run['id']}/steps/fail/execute", json={"approved": True}, headers=HEADERS)
    wait_done(client, run["id"], "fail")
    st = step_of(client.get(f"/api/v1/runs/{run['id']}").json(), "fail")
    assert st["status"] == "failed" and st["exit_code"] == 3


def test_modified_command_is_policy_checked_and_recorded(client):
    run = start(client)
    bad = client.post(f"/api/v1/runs/{run['id']}/steps/hello/execute",
                      json={"approved": True, "command": "notepad.exe"}, headers=HEADERS)
    assert bad.status_code == 403
    assert bad.json()["detail"]["allowed"] is False
    ok = client.post(f"/api/v1/runs/{run['id']}/steps/hello/execute",
                     json={"approved": True, "command": "ollama --help"}, headers=HEADERS)
    assert ok.status_code == 200
    wait_done(client, run["id"], "hello")
    st = step_of(client.get(f"/api/v1/runs/{run['id']}").json(), "hello")
    assert st["modified"] and st["executed_command"] == "ollama --help"
    actions = [e["action"] for e in client.get("/api/v1/audit").json()]
    assert "step.blocked" in actions and "step.executed" in actions


def test_evaluate_endpoint(client):
    run = start(client)
    r = client.post(f"/api/v1/runs/{run['id']}/steps/hello/evaluate",
                    json={"command": "git reset --hard"}, headers=HEADERS).json()
    assert r["allowed"] is False


def test_high_risk_needs_confirmation(client):
    run = start(client)
    r = client.post(f"/api/v1/runs/{run['id']}/steps/quota/execute", json={"approved": True}, headers=HEADERS)
    assert r.status_code == 428
    assert r.json()["detail"]["risk"] == "high"


def test_stop_long_running(client):
    run = start(client)
    client.post(f"/api/v1/runs/{run['id']}/steps/slow/execute", json={"approved": True}, headers=HEADERS)
    deadline = time.time() + 20
    while time.time() < deadline:
        if client.get(f"/api/v1/runs/{run['id']}/steps/slow/output").json()["lines"]:
            break
        time.sleep(0.1)
    again = client.post(f"/api/v1/runs/{run['id']}/steps/slow/execute", json={"approved": True}, headers=HEADERS)
    assert again.status_code == 409
    skip = client.post(f"/api/v1/runs/{run['id']}/steps/slow/skip", headers=HEADERS)
    assert skip.status_code == 409
    r = client.post(f"/api/v1/runs/{run['id']}/steps/slow/stop", headers=HEADERS)
    assert r.status_code == 200
    assert step_of(r.json(), "slow")["status"] == "stopped"


def test_stream_endpoint(client):
    run = start(client)
    client.post(f"/api/v1/runs/{run['id']}/steps/hello/execute", json={"approved": True}, headers=HEADERS)
    body = client.get(f"/api/v1/runs/{run['id']}/steps/hello/stream").text
    assert "hello from step" in body and "event: end" in body


def test_output_redacted(client):
    run = start(client)
    client.post(f"/api/v1/runs/{run['id']}/steps/secret/execute", json={"approved": True}, headers=HEADERS)
    out = "\n".join(wait_done(client, run["id"], "secret")["lines"])
    assert "AKIAABCDEFGHIJKLMNOP" not in out


def test_skip_and_completion(client):
    run = start(client)
    rid = run["id"]
    for sid in ("hello", "fail", "slow", "secret", "quota"):
        assert client.post(f"/api/v1/runs/{rid}/steps/{sid}/skip", headers=HEADERS).status_code == 200
    final = client.get(f"/api/v1/runs/{rid}").json()
    assert final["status"] == "completed"
    assert step_of(final, "optional-one")["status"] == "pending"


def test_check(client):
    run = start(client)
    r = client.post(f"/api/v1/runs/{run['id']}/steps/hello/check", json={"approved": True}, headers=HEADERS).json()
    assert r["passed"] and "verified" in r["output"]
    none = client.post(f"/api/v1/runs/{run['id']}/steps/fail/check", json={"approved": True}, headers=HEADERS)
    assert none.status_code == 404


def test_unknown_ids(client):
    assert client.get("/api/v1/runs/nope").status_code == 404
    assert client.post("/api/v1/runbooks/nope/runs", headers=HEADERS).status_code == 404
    run = start(client)
    assert client.post(f"/api/v1/runs/{run['id']}/steps/nope/skip", headers=HEADERS).status_code == 404


def test_usage_snapshot_without_services(client):
    r = client.get("/api/v1/usage?include_aws=false&include_remote=false")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "local" in data and isinstance(data["alerts"], list)
    s = client.post(f"/api/v1/usage/{data['id']}/summary", headers=HEADERS)
    assert s.status_code == 200, s.text
    assert s.json()["facts"]
    assert s.json()["source"] == "rules" and "Next:" in s.json()["text"]


def test_health_reports_down_services(client):
    data = client.get("/api/v1/health").json()
    names = {c["name"]: c for c in data["checks"]}
    assert names["database"]["status"] == "ok"
    assert names["ollama"]["status"] in ("error", "warn")
