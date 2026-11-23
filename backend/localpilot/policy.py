"""Command policy for runbook steps.

Every command (original or user-modified) passes through `CommandPolicy.evaluate` right before
execution. The policy is deliberately strict: each pipeline/statement must start with an allowlisted
executable, cmdlet or a script inside an allowed script directory; known destructive patterns are
blocked outright; and HTTP cmdlets may only talk to loopback addresses.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

RISK_ORDER = {"low": 0, "medium": 1, "high": 2}

ALLOWED_EXECUTABLES = {
    "python", "node", "npm", "git", "ollama", "aws", "code", "ssh", "scp", "ssh-keygen",
    "docker", "nvidia-smi", "where", "whoami", "hostname",
}

ALLOWED_CMDLETS = {
    "get-command", "get-process", "get-childitem", "get-content", "get-item", "get-date",
    "test-path", "test-netconnection", "select-string", "select-object", "where-object",
    "foreach-object", "format-table", "format-list", "measure-object", "sort-object",
    "convertto-json", "convertfrom-json", "out-string", "write-output", "write-host",
    "start-sleep", "invoke-restmethod", "invoke-webrequest", "join-path", "resolve-path",
}

HTTP_CMDLETS = {"invoke-restmethod", "invoke-webrequest", "irm", "iwr", "curl", "wget"}

DENY_PATTERNS: list[tuple[str, str]] = [
    (r"\brm\s+-[a-z]*r[a-z]*f?\s+/(\s|$)", "Deletes the root filesystem"),
    (r"\bremove-item\b[^\n]*-recurse", "Recursive delete is not allowed from a step"),
    (r"\b(rd|rmdir)\s+/s\b", "Recursive delete is not allowed from a step"),
    (r"\bdel\s+/[sq]\b", "Bulk delete is not allowed from a step"),
    (r"\bformat(\.com)?\s+[a-z]:", "Formats a drive"),
    (r"\bdiskpart\b", "Disk partitioning is not allowed"),
    (r"\b(iex|invoke-expression)\b", "Runs dynamically built or downloaded code"),
    (r"-encodedcommand\b|\s-enc\s", "Encoded commands hide what runs"),
    (r"\b(curl|wget|irm|iwr|invoke-webrequest|invoke-restmethod)\b[^\n]*\|\s*(sh|bash|pwsh|powershell)\b", "Pipes downloaded content into a shell"),
    (r"\b(stop-computer|restart-computer)\b|\bshutdown(\.exe)?\s+/[srp]", "Shuts down or restarts this computer"),
    (r"\bgit\s+reset\s+--hard\b", "Discards uncommitted work"),
    (r"\bgit\s+clean\s+-[a-z]*f", "Deletes untracked files"),
    (r"\bgit\s+push\b[^\n]*(--force|-f\b)", "Force-push rewrites shared history"),
    (r"\breg(\.exe)?\s+(add|delete|import)\b", "Edits the Windows registry"),
    (r"\bset-executionpolicy\b", "Changes the PowerShell execution policy"),
    (r"\baws\s+iam\s+(create|delete|attach|detach|put|update)", "Changes AWS IAM permissions"),
    (r"\baws\s+configure\s+set\b", "Changes stored AWS credentials or config"),
    (r"\bdocker\s+system\s+prune\b", "Deletes Docker data"),
]

HIGH_RISK_PATTERNS = [
    r"\baws\s+ec2\s+(run-instances|terminate-instances|start-instances|create-|delete-|authorize-|revoke-)",
    r"\baws\s+service-quotas\s+request-",
    r"\bdocker\s+(rm|rmi|volume\s+rm|run)\b",
]
MEDIUM_RISK_PATTERNS = [
    r"\bollama\s+(pull|rm|create)\b",
    r"\bnpm\s+(install|ci|i)\b",
    r"\bpip\s+install\b",
    r"\bcode\s+--(install|uninstall)-extension\b",
    r"\baws\s+ec2\s+stop-instances\b",
    r"\bgit\s+(commit|push|checkout|switch|merge|rebase|stash)\b",
]

_LOOPBACK_URL = re.compile(r"^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?(/|$)", re.I)
_URL = re.compile(r"https?://[^\s'\"]+", re.I)
_ASSIGN = re.compile(r"^\$[A-Za-z_][\w:]*\s*=\s*(.*)$", re.S)


class PolicyError(ValueError):
    pass


@dataclass
class PolicyDecision:
    allowed: bool
    risk: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "risk": self.risk, "reasons": self.reasons}


def max_risk(a: str, b: str) -> str:
    return a if RISK_ORDER[a] >= RISK_ORDER[b] else b


def split_statements(command: str) -> list[str]:
    """Split on ; | || && and newlines, ignoring separators inside quotes."""
    segments: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(command):
        c = command[i]
        if quote:
            buf.append(c)
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
            buf.append(c)
        elif c in ";|\n\r":
            segments.append("".join(buf))
            buf = []
            if c == "|" and command[i + 1 : i + 2] == "|":
                i += 1
        elif c == "&" and command[i + 1 : i + 2] == "&":
            segments.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(c)
        i += 1
    if quote:
        raise PolicyError("Unbalanced quotes in command")
    segments.append("".join(buf))
    return [s.strip() for s in segments if s.strip()]


class CommandPolicy:
    def __init__(self, repo_root: Path, extra_script_dirs: list[Path] | None = None) -> None:
        self.repo_root = repo_root.resolve()
        self.script_dirs = [self.repo_root / "deploy", self.repo_root / "scripts", *(extra_script_dirs or [])]
        self.trusted_exes = {Path(sys.executable).resolve()}

    def evaluate(self, command: str, declared_risk: str = "low") -> PolicyDecision:
        reasons: list[str] = []
        lowered = command.lower()
        for pattern, why in DENY_PATTERNS:
            if re.search(pattern, lowered):
                reasons.append(f"Blocked: {why}")
        try:
            statements = split_statements(command)
        except PolicyError as e:
            return PolicyDecision(False, "high", [str(e)])
        if not statements:
            return PolicyDecision(False, declared_risk, ["Empty command"])
        for st in statements:
            problem = self._check_statement(st)
            if problem:
                reasons.append(problem)

        risk = declared_risk
        if any(re.search(p, lowered) for p in HIGH_RISK_PATTERNS):
            risk = max_risk(risk, "high")
        elif any(re.search(p, lowered) for p in MEDIUM_RISK_PATTERNS):
            risk = max_risk(risk, "medium")
        return PolicyDecision(not reasons, risk, reasons)

    def _check_statement(self, st: str) -> str | None:
        m = _ASSIGN.match(st)
        if m:
            rhs = m.group(1).strip()
            if not rhs or rhs[0] in "\"'0123456789" or rhs.lower() in ("$true", "$false", "$null"):
                return None
            return self._check_statement(rhs)
        if st.startswith("&"):
            st = st[1:].strip()
        if st[:1] in "({@[":
            if st.lower().startswith("[environment]::getenvironmentvariable("):
                return None
            return "Complex PowerShell expressions are not allowed in a step; put the logic in a script under deploy/ or scripts/"
        token = _first_token(st)
        name = token.lower()
        if name.endswith(".ps1") or "/" in token or "\\" in token:
            return self._check_path(token)
        if name.endswith(".exe"):
            name = name[:-4]
        if name in HTTP_CMDLETS:
            urls = _URL.findall(st)
            if not urls:
                return f"{token}: target URL must be given explicitly"
            bad = [u for u in urls if not _LOOPBACK_URL.match(u)]
            if bad:
                return f"{token}: only loopback URLs are allowed from steps (got {bad[0]})"
            return None
        if name in ALLOWED_EXECUTABLES or name in ALLOWED_CMDLETS:
            return None
        return f"'{token}' is not on the allowlist"

    def _check_path(self, token: str) -> str | None:
        p = Path(token)
        if not p.is_absolute():
            p = self.repo_root / p
        try:
            p = p.resolve()
        except OSError:
            return f"Cannot resolve path {token}"
        if p.suffix.lower() == ".ps1":
            if not p.is_file():
                return f"Script not found: {token}"
            if not any(_is_within(p, d) for d in self.script_dirs):
                return f"Scripts must live under deploy/ or scripts/ (got {token})"
            return None
        if p in self.trusted_exes:
            return None
        base = p.stem.lower()
        if base in ALLOWED_EXECUTABLES and any(_is_within(p, d) for d in self.script_dirs):
            return None
        return f"Executable path is not trusted: {token}"


def _first_token(st: str) -> str:
    st = st.strip()
    if st[:1] in "\"'":
        q = st[0]
        end = st.find(q, 1)
        return st[1:end] if end > 0 else st[1:]
    return st.split(None, 1)[0]


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
        return True
    except ValueError:
        return False
