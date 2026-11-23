from __future__ import annotations

import json

from localpilot.usage.rules import compact_facts, plain_summary
from localpilot.usage.summarizer import ungrounded_numbers

SNAP = {"local": {"cpu_percent": 11.6, "ram_used_percent": 74.1, "top_processes": [{"name": "chrome.exe", "rss_mb": 543}]},
        "ollama": {"reachable": True, "loaded": []}, "aws": {"instances": []}}


def test_ungrounded_numbers_flags_invented_values():
    facts = compact_facts(SNAP, [])
    payload = json.dumps(facts)
    assert ungrounded_numbers("- RAM is 74.1% used, CPU 11.6%", payload) == []
    assert ungrounded_numbers("- Upgrade RAM to 128GB", payload) == ["128"]


def test_plain_summary_is_deterministic_and_grounded():
    facts = compact_facts(SNAP, [])
    text = plain_summary(facts)
    assert "74.1%" in text and "no compute cost" in text and "Nothing to do" in text
    assert ungrounded_numbers(text, json.dumps(facts)) == []


def test_warnings_appear_in_summary():
    facts = compact_facts(SNAP, [{"level": "warn", "text": "Only 5 GB free on C:\\."}])
    assert "Attention: Only 5 GB free" in plain_summary(facts)
    assert facts["suggested_action"] == "Fix the warnings listed above."


def test_running_instance_drives_action():
    snap = {**SNAP, "aws": {"instances": [{"state": "running", "type": "t3.medium", "running_hours_since_start": 1.5,
                                           "hourly_usd": 0.0432}]}}
    facts = compact_facts(snap, [])
    assert "stop.ps1" in facts["suggested_action"]
    assert "t3.medium" in plain_summary(facts)
