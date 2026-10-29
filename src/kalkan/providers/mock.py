"""Offline provider. Responses are computed from the prompt payload, not from a network call."""

from __future__ import annotations

from kalkan.attacker.mutations import mutate_seeds
from kalkan.config import assert_standard_model
from kalkan.judge.rules import deterministic_verdict, payload_from_messages


class MockProvider:
    mode = "mock"

    def complete_json(
        self,
        *,
        model: str,
        messages: list[dict],
        schema_name: str,
        schema: dict,
        reasoning_effort: str,
    ) -> dict:
        assert_standard_model(model)
        if reasoning_effort == "none":
            raise ValueError("Muse Spark rejects reasoning_effort 'none'.")
        payload = payload_from_messages(messages)
        if schema_name == "kalkan_verdict":
            return deterministic_verdict(payload)
        if schema_name == "kalkan_attacks":
            return mutate_seeds(payload["seeds"])
        raise ValueError(f"Mock provider has no response for schema {schema_name}.")
