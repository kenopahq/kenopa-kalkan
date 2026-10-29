"""Model provider interface. Live and mock paths share this shape."""

from __future__ import annotations

from typing import Protocol


class ModelProvider(Protocol):
    mode: str

    def complete_json(
        self,
        *,
        model: str,
        messages: list[dict],
        schema_name: str,
        schema: dict,
        reasoning_effort: str,
    ) -> dict:
        """Return a JSON object constrained to `schema`."""
