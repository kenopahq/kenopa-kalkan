"""Meta Model API client. OpenAI-SDK compatible, Standard model IDs only."""

from __future__ import annotations

import json

from kalkan.config import api_key, assert_standard_model

META_BASE_URL = "https://api.meta.ai/v1"


class MetaProvider:
    mode = "meta"

    def __init__(self, client):
        self.client = client

    @classmethod
    def from_env(cls) -> MetaProvider:
        key = api_key()
        if not key:
            raise RuntimeError("META_API_KEY or MODEL_API_KEY is required for the Meta provider.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is required for the Meta provider.") from exc
        client = OpenAI(base_url=META_BASE_URL, api_key=key)
        return cls(client)

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
            raise ValueError("Muse models reject reasoning_effort 'none' on Chat Completions.")
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": schema_name, "schema": schema},
            },
            extra_body={"reasoning_effort": reasoning_effort},
        )
        content = response.choices[0].message.content or ""
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("Meta Model API returned content that is not JSON.") from exc
