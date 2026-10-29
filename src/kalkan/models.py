"""Shared request and decision types."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Action = Literal["allow", "block", "confirm"]
Sensitivity = Literal["low", "medium", "high", "critical"]


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("arguments", mode="before")
    @classmethod
    def _coerce_arguments(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {"raw": value}
            if isinstance(parsed, dict):
                return parsed
            return {"raw": parsed}
        if isinstance(value, dict):
            return value
        return {"raw": value}


class ScreenResult(BaseModel):
    label: Literal["MALICIOUS", "BENIGN"]
    score: float
    backend: str
    matched_rule_ids: list[str] = Field(default_factory=list)
    backend_note: str = ""


class JudgeVerdict(BaseModel):
    action: Action
    rule_id: str
    explanation: str
    intent_match: bool


class Decision(BaseModel):
    action: Action
    rule_id: str
    explanation: str
    intent_match: bool
    pass_fired: Literal[1, 2, "policy"]
    screen: ScreenResult
    judge: JudgeVerdict | None = None
    judge_backend: str
    overridden_by_policy: bool = False
    tool: ToolCall


class EvalCase(BaseModel):
    id: str
    language: Literal["en", "tr"]
    split: Literal["train", "heldout"]
    kind: Literal["attack", "benign"]
    technique: str
    user_intent: str
    untrusted: str
    tool: ToolCall
    expect: Action
    notes: str = ""
