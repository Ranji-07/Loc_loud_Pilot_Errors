from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import psutil
import yaml

from ..config import Settings

REMOTE_PROBE = (
    "echo \"gpu=$(nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu "
    "--format=csv,noheader,nounits 2>/dev/null | head -1)\"; "
    "echo \"mem=$(free -m | awk '/Mem:/ {print $2\",\"$3}')\"; "
    "echo \"disk=$(df -BG / | awk 'NR==2 {print $2\",\"$3\",\"$4}')\"; "
    "echo \"uptime=$(cut -d. -f1 /proc/uptime)\"; "
    "echo \"idle=$(cat /var/lib/localpilot/idle-minutes 2>/dev/null)\"; "
    "echo \"ollama_ps=$(curl -s --max-time 3 http://127.0.0.1:11434/api/ps | tr -d '\\n')\""
)


def load_pricing(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def local_system(settings: Settings) -> dict[str, Any]:
    vm = psutil.virtual_memory()
    anchors = {str(settings.data_dir.anchor or settings.data_dir)}
    if Path("C:\\").exists():
        anchors.add("C:\\")
    disks = []
    for a in sorted(anchors):
        try:
            du = psutil.disk_usage(a)
            disks.append({"mount": a, "free_gb": round(du.free / 1e9, 1), "total_gb": round(du.total / 1e9, 1),
                          "used_percent": du.percent})
        except OSError:
            continue
    procs = []
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            procs.append((p.info["memory_info"].rss, p.info["name"]))
        except (psutil.Error, AttributeError, TypeError):
            continue
    top = [{"name": n, "rss_mb": round(r / 1e6)} for r, n in sorted(procs, reverse=True)[:6]]
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "cpu_count": psutil.cpu_count(),
        "ram_total_gb": round(vm.total / 1e9, 1),
        "ram_used_percent": vm.percent,
        "ram_available_gb": round(vm.available / 1e9, 1),
        "disks": disks,
        "top_processes": top,
    }


def local_gpu() -> dict[str, Any]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"available": False, "reason": "No NVIDIA GPU / driver on this machine"}
    r = subprocess.run([exe, "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                        "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
    gpus = []
    for line in r.stdout.strip().splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) == 4:
            gpus.append({"name": parts[0], "mem_used_mb": int(parts[1]), "mem_total_mb": int(parts[2]),
                         "util_percent": int(parts[3])})
    return {"available": bool(gpus), "gpus": gpus}


async def ollama_state(url: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            ps = (await c.get(f"{url}/api/ps")).json().get("models", [])
            tags = (await c.get(f"{url}/api/tags")).json().get("models", [])
    except httpx.HTTPError:
        return {"reachable": False, "url": url}
    return {
        "reachable": True,
        "url": url,
        "installed": [{"name": m.get("name"), "size_gb": round(m.get("size", 0) / 1e9, 2)} for m in tags],
        "loaded": [{"name": m.get("name"), "size_gb": round(m.get("size", 0) / 1e9, 2),
                    "vram_gb": round(m.get("size_vram", 0) / 1e9, 2), "expires_at": m.get("expires_at")} for m in ps],
    }


def aws_instances(settings: Settings, pricing: dict[str, Any]) -> dict[str, Any]:
    exe = shutil.which("aws")
    if not exe:
        return {"available": False, "reason": "AWS CLI not installed"}
    query = ("Reservations[].Instances[].{id:InstanceId,type:InstanceType,state:State.Name,"
             "launch:LaunchTime,ip:PublicIpAddress,name:Tags[?Key=='Name']|[0].Value,"
             "volumes:BlockDeviceMappings[].Ebs.VolumeId}")
    r = subprocess.run([exe, "ec2", "describe-instances", "--region", settings.aws_region,
                        "--filters", "Name=tag:LocalPilot,Values=*",
                        "Name=instance-state-name,Values=pending,running,stopping,stopped",
                        "--query", query, "--output", "json"],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return {"available": False, "reason": "AWS CLI call failed (credentials or network)"}
    region_prices = pricing.get("aws", {}).get(settings.aws_region, {})
    prices = region_prices.get("instances", {})
    now = datetime.now(timezone.utc)
    out = []
    for inst in json.loads(r.stdout or "[]"):
        hourly = prices.get(inst["type"])
        hours = None
        if inst["state"] == "running" and inst.get("launch"):
            launched = datetime.fromisoformat(inst["launch"].replace("Z", "+00:00"))
            hours = round((now - launched).total_seconds() / 3600, 2)
        out.append({
            "id": inst["id"], "name": inst.get("name"), "type": inst["type"], "state": inst["state"],
            "running_hours_since_start": hours, "hourly_usd": hourly,
            "cost_since_start_usd": round(hours * hourly, 3) if hours is not None and hourly else None,
        })
    return {"available": True, "region": settings.aws_region, "instances": out,
            "ebs_gp3_gb_month_usd": region_prices.get("ebs_gp3_gb_month"),
            "pricing_source": pricing.get("source")}


def remote_target(settings: Settings) -> dict[str, Any]:
    f = settings.aws_state_file
    if not f.exists():
        return {"configured": False}
    state = json.loads(f.read_text(encoding="utf-8"))
    host, user, key = state.get("public_ip"), state.get("ssh_user", "ubuntu"), state.get("key_path")
    if not host or not key:
        return {"configured": True, "reachable": False, "reason": "Target has no public IP (stopped?)",
                "instance_id": state.get("instance_id")}
    ssh = shutil.which("ssh")
    if not ssh:
        return {"configured": True, "reachable": False, "reason": "OpenSSH client not found"}
    try:
        r = subprocess.run([ssh, "-i", key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=6",
                            "-o", "StrictHostKeyChecking=accept-new", f"{user}@{host}", REMOTE_PROBE],
                           capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return {"configured": True, "reachable": False, "reason": "SSH timed out"}
    if r.returncode != 0:
        return {"configured": True, "reachable": False, "reason": "SSH failed", "instance_id": state.get("instance_id")}
    return {"configured": True, "reachable": True, "instance_id": state.get("instance_id"),
            "instance_type": state.get("instance_type"), **parse_remote(r.stdout)}


def parse_remote(text: str) -> dict[str, Any]:
    kv = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip()
    res: dict[str, Any] = {}
    gpu = [x.strip() for x in kv.get("gpu", "").split(",")]
    if len(gpu) == 4 and gpu[0]:
        res["gpu"] = {"name": gpu[0], "mem_used_mb": _int(gpu[1]), "mem_total_mb": _int(gpu[2]), "util_percent": _int(gpu[3])}
    else:
        res["gpu"] = None
    mem = kv.get("mem", "").split(",")
    if len(mem) == 2:
        res["ram_total_mb"], res["ram_used_mb"] = _int(mem[0]), _int(mem[1])
    disk = kv.get("disk", "").replace("G", "").split(",")
    if len(disk) == 3:
        res["disk_total_gb"], res["disk_used_gb"], res["disk_free_gb"] = (_int(x) for x in disk)
    res["uptime_hours"] = round(_int(kv.get("uptime", "0")) / 3600, 2)
    res["idle_minutes"] = _int(kv.get("idle", "")) if kv.get("idle") else None
    try:
        res["ollama_loaded"] = [m.get("name") for m in json.loads(kv.get("ollama_ps") or "{}").get("models", [])]
    except ValueError:
        res["ollama_loaded"] = None
    return res


def _int(v: str) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0
