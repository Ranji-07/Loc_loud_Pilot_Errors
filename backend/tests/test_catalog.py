from __future__ import annotations

import asyncio
import logging
import csv
import io

import httpx

from localpilot import audit, catalog
from localpilot.config import Settings
from localpilot.models import ModelCall

from .test_agents import agent_client, fake_models  # noqa: F401  (fixture reuse)


def _seed(db) -> None:
    audit.record(db, "approval.requested", "run-1", actor="system")
    audit.record(db, "approval.denied", "run-1", actor="user:dashboard")
    audit.record(db, "agent.succeeded", "run-2", actor="system")
    audit.record(db, "runbook.step.executed", "key AKIAABCDEFGHIJKLMNOP", actor="user:vscode")


def test_audit_filters_and_cursor_paging(client):
    _seed(client.app.state.db)
    get = lambda **p: client.get("/api/v1/audit", params=p).json()
    assert [e["action"] for e in get(action="approval.")] == ["approval.denied", "approval.requested"]
    assert [e["actor"] for e in get(actor="user:")] == ["user:vscode", "user:dashboard"]
    assert [e["target"] for e in get(q="run-2")] == ["run-2"]
    assert get(q="%") == []  # LIKE wildcards are escaped
    first = get(limit=2)
    second = get(limit=2, before=first[-1]["id"])
    assert len(first) == 2 and second and second[0]["id"] < first[-1]["id"]
    assert not {e["id"] for e in first} & {e["id"] for e in second}
    assert get(since="2999-01-01") == [] and get(until="2000-01-01") == []
    actions = {a["action"]: a["count"] for a in client.get("/api/v1/audit/actions").json()}
    assert actions["approval.denied"] == 1 and "server.started" in actions


def test_audit_export_is_redacted_download(client):
    _seed(client.app.state.db)
    r = client.get("/api/v1/audit/export", params={"actor": "user:vscode"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    assert "AKIAABCDEFGHIJKLMNOP" not in r.text and "AKIA****" in r.text
    assert r.text.splitlines()[0] == "id,at,actor,action,target,detail" and len(r.text.splitlines()) == 2
    j = client.get("/api/v1/audit/export", params={"format": "json", "action": "approval."}).json()
    assert [e["action"] for e in j] == ["approval.denied", "approval.requested"]
    assert client.get("/api/v1/audit/export", params={"format": "xml"}).status_code == 422


def test_model_calls_by_day_and_cache_is_local(client):
    with client.app.state.db.session() as s:
        s.add(ModelCall(task="usage-summary", provider="ollama", model="qwen2.5:0.5b", input_hash="a"))
        s.add(ModelCall(task="usage-summary", provider="cache", model="qwen2.5:0.5b", input_hash="a", cached=True))
        s.add(ModelCall(task="droid-agent", provider="factory", model="haiku", input_hash="b", credits=10))
    data = client.get("/api/v1/usage/model-calls").json()
    assert data["totals"]["local"]["calls"] == 2 and data["totals"]["cloud"]["credits"] == 10
    assert len(data["by_day"]) == 1
    assert data["by_day"][0] | {"day": None} == {"day": None, "local_calls": 2, "cloud_calls": 1, "credits": 10.0}


def test_settings_cover_every_field_and_hide_secrets(client, settings: Settings):
    data = client.get("/api/v1/settings").json()
    names = [s["name"] for g in data["groups"] for s in g["settings"]]
    assert sorted(names) == sorted(Settings.model_fields) and len(names) == len(set(names))
    rows = {s["name"]: s for g in data["groups"] for s in g["settings"]}
    assert rows["port"]["is_default"] and rows["port"]["env"] == "LOCALPILOT_PORT"
    assert not rows["data_dir"]["is_default"] and rows["data_dir"]["value"] == str(settings.data_dir)
    assert rows["runbooks_dir"]["value"] == str(settings.runbooks_dir)
    assert data["editable"] is False
    scrubbed = catalog._scrub({"apiKey": "sk-123", "url": "http://bob:pw@host:9/x", "n": [1]})
    assert scrubbed == {"apiKey": "hidden", "url": "http://hidden@host:9/x", "n": [1]}


def test_log_tail_is_redacted(client, settings: Settings):
    logging.getLogger("localpilot").info("token=supersecretvalue1 done", extra={"target": "x", "apiKey": "nested-secret"})
    for h in logging.getLogger("localpilot").handlers:
        h.flush()
    lines = client.get("/api/v1/system/logs", params={"lines": 5}).json()["lines"]
    last = lines[-1]
    assert last["level"] == "INFO" and "supersecretvalue1" not in last["msg"] and last["extra"]["target"] == "x"
    assert last["extra"]["apiKey"] == "hidden"


def test_settings_scrub_url_queries_and_preserve_token_limits():
    data = catalog._scrub({"url": "http://user:pass@[::1]:9/x?token=private&mode=chat",
                          "maxOutputTokens": 4096, "baseUrl": "http://host/v1?api_key=private"})
    assert "private" not in str(data) and "pass" not in str(data)
    assert "[::1]:9" in data["url"] and data["maxOutputTokens"] == 4096


def test_csv_formula_guard_and_json_validity(client):
    audit.record(client.app.state.db, "agent.test", "=1+1", apiKey="secret", notes="token=secret end")
    r = client.get("/api/v1/audit/export", params={"action": "agent.test"})
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[1][4] == "'=1+1" and "secret" not in r.text
    j = client.get("/api/v1/audit/export", params={"format": "json", "action": "agent.test"}).json()
    assert j[0]["detail"]["apiKey"] == "hidden"


def test_ollama_catalog_reads_show_details():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "localpilot-coder:latest", "size": 4_683_087_225}]})
        if request.url.path == "/api/ps":
            return httpx.Response(200, json={"models": [{"name": "localpilot-coder:latest", "size": 6e9, "size_vram": 0}]})
        return httpx.Response(200, json={
            "details": {"family": "qwen2", "parameter_size": "7.6B", "quantization_level": "Q4_K_M",
                        "parent_model": "qwen2.5-coder:7b"},
            "model_info": {"qwen2.context_length": 32768}, "parameters": "num_ctx                        24576\n",
            "capabilities": ["completion", "tools"]})

    out = asyncio.run(catalog.ollama_models("http://ollama", transport=httpx.MockTransport(handler)))
    m = out["models"][0]
    assert out["reachable"] and m["max_context"] == 32768 and m["configured_context"] == 24576
    assert m["loaded"] and m["loaded_gb"] == 6.0 and m["loaded_on_gpu_gb"] == 0 and m["size_gb"] == 4.68


def test_models_endpoint_offline_ollama_and_droid_usage(agent_client):  # noqa: F811
    with agent_client.app.state.db.session() as s:
        s.add(ModelCall(task="droid-agent", provider="factory", model="claude-haiku-4-5-20251001",
                        input_hash="r", prompt_tokens=5, credits=7))
    data = agent_client.get("/api/v1/models").json()
    assert data["local"]["reachable"] is False and data["remote"]["reason"]
    haiku = next(m for m in data["droid"]["models"] if m["id"] == "claude-haiku-4-5-20251001")
    assert haiku["default"] and haiku["calls"] == 1 and haiku["credits"] == 7
    assert {r["task"] for r in data["routing"]} == {"Usage summaries", "Droid tasks"}
