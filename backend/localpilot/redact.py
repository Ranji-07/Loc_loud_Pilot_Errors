from __future__ import annotations

import re

_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AKIA****************"),
    (re.compile(r"ASIA[0-9A-Z]{16}"), "ASIA****************"),
    (re.compile(r"(?i)(aws_secret_access_key|secret[_-]?key|api[_-]?key|token|password)(\s*[:=]\s*)\S+"), r"\1\2****"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{12,}"), "Bearer ****"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "-----BEGIN PRIVATE KEY (redacted)-----"),
    (re.compile(r"\b\d{12}\b"), "<aws-account>"),
]


def redact(line: str) -> str:
    for pat, repl in _PATTERNS:
        line = pat.sub(repl, line)
    return line
