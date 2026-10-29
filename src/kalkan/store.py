"""Append-only decision log for the dashboard."""

from __future__ import annotations

import json
from pathlib import Path


class EventLog:
    def __init__(self, path: Path | None = None):
        self.path = path
        self.events: list[dict] = []
        if path and path.is_file():
            lines = path.read_text(encoding="utf-8").splitlines()[-500:]
            for line in lines:
                if line.strip():
                    self.events.append(json.loads(line))

    def add(self, event: dict) -> None:
        self.events.append(event)
        if len(self.events) > 500:
            self.events = self.events[-500:]
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def recent(self, limit: int = 50) -> list[dict]:
        return list(reversed(self.events[-limit:]))
