"""Deterministic usage rules. These produce the facts and alerts; the small model only rephrases them."""
from __future__ import annotations

from typing import Any


def evaluate(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    sysinfo = snapshot.get("local", {})
    ram = sysinfo.get("ram_used_percent")
    if ram is not None and ram >= 85:
        alerts.append({"level": "warn", "text": f"Laptop RAM is {ram:.0f}% used. Close heavy apps or unload Ollama models."})
    for d in sysinfo.get("disks", []):
        if d["free_gb"] < 10:
            alerts.append({"level": "warn", "text": f"Only {d['free_gb']} GB free on {d['mount']}."})

    oll = snapshot.get("ollama", {})
    if not oll.get("reachable"):
        alerts.append({"level": "warn", "text": "Local Ollama is not running."})
    else:
        for m in oll.get("loaded", []):
            alerts.append({"level": "info", "text": f"Local model {m['name']} is loaded ({m['size_gb']} GB)."})

    aws = snapshot.get("aws", {})
    remote = snapshot.get("remote", {})
    for inst in aws.get("instances", []) or []:
        if inst["state"] == "running":
            cost = inst.get("cost_since_start_usd")
            cost_txt = f", about ${cost:.2f} so far" if cost is not None else ""
            level = "warn" if (inst.get("running_hours_since_start") or 0) >= 2 else "info"
            alerts.append({"level": level, "text": f"AWS {inst['type']} {inst['id']} is running and billing"
                                                   f" (${inst.get('hourly_usd')}/h{cost_txt})."})
            if remote.get("configured") and not remote.get("reachable"):
                alerts.append({"level": "warn", "text": "The AWS instance is running but LocalPilot cannot reach it over SSH."})
        elif inst["state"] == "stopped":
            alerts.append({"level": "info", "text": f"AWS {inst['id']} is stopped: no compute charge, its disk is still billed."})

    if remote.get("reachable"):
        gpu = remote.get("gpu")
        if gpu and gpu.get("util_percent", 0) < 5 and not remote.get("ollama_loaded"):
            alerts.append({"level": "info", "text": f"Remote GPU {gpu['name']} is idle with no model loaded. Stop the instance if you are done."})
    if not alerts:
        alerts.append({"level": "ok", "text": "Nothing needs attention."})
    return alerts


def suggested_action(snapshot: dict[str, Any], alerts: list[dict[str, str]]) -> str:
    running = [i for i in (snapshot.get("aws", {}).get("instances") or []) if i["state"] == "running"]
    if running:
        return "Stop the AWS instance with deploy/aws/stop.ps1 when you are not using it."
    if any(a["level"] == "warn" for a in alerts):
        return "Fix the warnings listed above."
    if snapshot.get("ollama", {}).get("loaded"):
        return "Nothing to do; Ollama unloads idle models automatically."
    return "Nothing to do."


def plain_summary(facts: dict[str, Any]) -> str:
    lap = facts["laptop"]
    lines = [f"- Laptop: CPU {lap['cpu']}%, RAM {lap['ram_pct']}% used; biggest processes: {', '.join(lap['top']) or 'n/a'}."]
    lines += [f"- Attention: {w}" for w in facts.get("warnings", [])]
    cost = ", ".join(facts["aws_running"]) if facts["aws_running"] else "nothing is running on AWS, so no compute cost"
    lines.append(f"- Cost right now: {cost}.")
    lines.append(f"- Next: {facts['suggested_action']}")
    return "\n".join(lines)


def compact_facts(snapshot: dict[str, Any], alerts: list[dict[str, str]]) -> dict[str, Any]:
    local = snapshot.get("local", {})
    return {
        "suggested_action": suggested_action(snapshot, alerts),
        "laptop": {"cpu": local.get("cpu_percent"), "ram_pct": local.get("ram_used_percent"),
                   "top": [p["name"] for p in local.get("top_processes", [])[:3]]},
        "local_models_loaded": [m["name"] for m in snapshot.get("ollama", {}).get("loaded", [])],
        "aws_running": [f"{i['type']} {i.get('running_hours_since_start')}h ${i.get('hourly_usd')}/h"
                        for i in (snapshot.get("aws", {}).get("instances") or []) if i["state"] == "running"],
        "alerts": [a["text"] for a in alerts if a["level"] != "ok"],
        "warnings": [a["text"] for a in alerts if a["level"] in ("warn", "error")],
    }
