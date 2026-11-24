"""Capture and audit the running real dashboard, without sending prompts."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dashboard_checks", ROOT / "scripts/check-dashboard.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
checks.SESSION = os.environ.get("AGENT_BROWSER_SESSION", "localpilot-ui-capture")
browser, evaluate = checks.browser, checks.evaluate
BASE = "http://127.0.0.1:8765"
OUT = ROOT / ".screens"
PAGES = [
    ("overview", "Overview"), ("projects", "Projects"), ("agents", "Agents"),
    ("tasks", "Tasks"), ("prompts", "Prompt Studio"), ("decisions", "Decisions"),
    ("knowledge", "Knowledge"), ("history", "History"), ("models", "Models"),
    ("infrastructure", "Infrastructure"), ("costs", "Costs"), ("settings", "Settings"),
    ("agents/performance", "Agents"), ("agents/permissions", "Agents"),
    ("infrastructure/resources", "Infrastructure"), ("infrastructure/logs", "Infrastructure"),
    ("infrastructure/setup", "Infrastructure"), ("decisions/decisions", "Decisions"),
]


def main():
    OUT.mkdir(exist_ok=True)
    results = []
    pages = [item for item in PAGES if item[0] in sys.argv[1:]] if len(sys.argv) > 1 else PAGES
    try:
        browser("open", BASE)
        for theme in ("dark", "light"):
            evaluate(f"localStorage.setItem('localpilot.theme', '{theme}'); document.documentElement.dataset.theme = '{theme}'")
            for width, name in ((1366, "desktop"), (820, "tablet"), (390, "mobile")):
                browser("set", "viewport", str(width), "900")
                for page, title in pages:
                    browser("open", f"{BASE}/#/{page}")
                    browser("wait", "--fn", f"document.querySelector('#main h1')?.textContent === {json.dumps(title)}")
                    browser("wait", "--fn", "!document.querySelector('#main [role=status]')")
                    overflow = evaluate("document.documentElement.scrollWidth > innerWidth")["result"]
                    shot = OUT / f"step10-{page.replace('/', '-')}-{theme}-{name}.png"
                    browser("screenshot", str(shot))
                    result = {"page": page, "theme": theme, "width": width, "overflow": overflow, "screenshot": shot.name}
                    if name == "desktop":
                        audit = browser("a11y")
                        result["a11y"] = audit["counts"]
                        result["violations"] = audit["violations"]
                    errors = browser("errors")
                    result["errors"] = errors.get("errors", [])
                    results.append(result)
                    print(json.dumps(result), flush=True)
        report = OUT / "step10-browser-report.json"
        if len(sys.argv) > 1 and report.exists():
            previous = json.loads(report.read_text(encoding="utf-8"))
            keys = {(r["page"], r["theme"], r["width"]) for r in results}
            results = [r for r in previous if (r["page"], r["theme"], r["width"]) not in keys] + results
        report.write_text(json.dumps(results, indent=2), encoding="utf-8")
        failures = [r for r in results if r["overflow"] or r["errors"] or r.get("a11y", {}).get("violations", 0)]
        print(json.dumps({"screenshots": len(results), "failures": len(failures)}), flush=True)
        if failures:
            raise AssertionError(f"{len(failures)} browser checks failed; see .screens/step10-browser-report.json")
    finally:
        browser("close")


if __name__ == "__main__":
    main()
