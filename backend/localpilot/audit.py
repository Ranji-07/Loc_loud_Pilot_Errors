from __future__ import annotations

import logging
from typing import Any

from .db import Database
from .models import AuditEvent

log = logging.getLogger("localpilot.audit")


def record(db: Database, action: str, target: str, actor: str = "user", **detail: Any) -> None:
    with db.session() as s:
        s.add(AuditEvent(actor=actor, action=action, target=target, detail=detail))
    log.info(action, extra={"target": target, "actor": actor})
