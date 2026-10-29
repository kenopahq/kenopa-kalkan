"""Load the tool policy from YAML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from kalkan.models import Sensitivity


@dataclass(frozen=True)
class ToolMeta:
    name: str
    sensitivity: Sensitivity
    description: str


@dataclass(frozen=True)
class Rule:
    id: str
    description: str


@dataclass(frozen=True)
class Policy:
    name: str
    version: int
    description: str
    hard_deny: frozenset[str]
    tools: dict[str, ToolMeta]
    rules: tuple[Rule, ...]

    def tool(self, name: str) -> ToolMeta:
        known = self.tools.get(name)
        if known:
            return known
        return ToolMeta(name=name, sensitivity="high", description="Unknown tool.")

    def rule_map(self) -> dict[str, str]:
        return {rule.id: rule.description for rule in self.rules}

    def public_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description.strip(),
            "hard_deny": sorted(self.hard_deny),
            "tools": {
                name: {"sensitivity": meta.sensitivity, "description": meta.description}
                for name, meta in self.tools.items()
            },
            "rules": [{"id": rule.id, "description": rule.description} for rule in self.rules],
        }


def load_policy(path: Path) -> Policy:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    tools = {
        name: ToolMeta(
            name=name,
            sensitivity=spec["sensitivity"],
            description=spec.get("description", ""),
        )
        for name, spec in raw["tools"].items()
    }
    rules = tuple(Rule(id=item["id"], description=item["description"]) for item in raw["rules"])
    return Policy(
        name=raw["name"],
        version=int(raw["version"]),
        description=raw.get("description", ""),
        hard_deny=frozenset(raw.get("hard_deny", [])),
        tools=tools,
        rules=rules,
    )
