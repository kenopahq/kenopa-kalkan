"""Pattern screen used when Prompt Guard weights are not loaded."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from kalkan.models import ScreenResult
from kalkan.text import normalize


@dataclass(frozen=True)
class Pattern:
    id: str
    regex: re.Pattern[str]


def load_patterns(path: Path) -> list[Pattern]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    patterns: list[Pattern] = []
    for item in raw["patterns"]:
        patterns.append(Pattern(id=item["id"], regex=re.compile(item["regex"])))
    return patterns


class HeuristicScreen:
    backend = "heuristic"

    def __init__(self, patterns: list[Pattern], backend_note: str = "", extra: list[Pattern] | None = None):
        self.base_patterns = list(patterns)
        self.extra_patterns = list(extra or [])
        self.backend_note = backend_note

    @property
    def patterns(self) -> list[Pattern]:
        return [*self.base_patterns, *self.extra_patterns]

    def with_extra(self, extra: list[Pattern]) -> HeuristicScreen:
        return HeuristicScreen(self.base_patterns, backend_note=self.backend_note, extra=extra)

    def scan(self, text: str) -> ScreenResult:
        folded = normalize(text)
        matched = [pattern.id for pattern in self.patterns if pattern.regex.search(folded)]
        if matched:
            # More matching rules mean a higher heuristic score. Cap at 0.99.
            score = min(0.99, 0.55 + 0.1 * len(matched))
            return ScreenResult(
                label="MALICIOUS",
                score=round(score, 4),
                backend=self.backend,
                matched_rule_ids=matched,
                backend_note=self.backend_note,
            )
        return ScreenResult(
            label="BENIGN",
            score=0.05,
            backend=self.backend,
            matched_rule_ids=[],
            backend_note=self.backend_note,
        )
