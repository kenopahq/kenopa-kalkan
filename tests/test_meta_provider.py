import json
from pathlib import Path

import pytest

from kalkan.config import ConfigError, load_settings
from kalkan.providers.meta import META_BASE_URL, MetaProvider
from kalkan.providers.mock import MockProvider


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "recorded" / "spark_verdict_block.json"


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        content = json.loads(FIXTURE.read_text(encoding="utf-8"))["choices"][0]["message"]["content"]
        return _Response(content)


class _Chat:
    def __init__(self):
        self.completions = _Completions()


class _Client:
    def __init__(self):
        self.chat = _Chat()


def test_recorded_fixture_parses_as_a_block_verdict():
    client = _Client()
    provider = MetaProvider(client)
    verdict = provider.complete_json(
        model="muse-spark-1.3",
        messages=[{"role": "user", "content": "KALKAN_PAYLOAD {}"}],
        schema_name="kalkan_verdict",
        schema={"type": "object", "additionalProperties": False},
        reasoning_effort="low",
    )
    assert verdict["action"] == "block"
    assert verdict["rule_id"] == "no-instruction-override"
    sent = client.chat.completions.kwargs
    assert sent["model"] == "muse-spark-1.3"
    assert sent["response_format"]["type"] == "json_schema"
    assert sent["response_format"]["json_schema"]["name"] == "kalkan_verdict"
    assert sent["extra_body"]["reasoning_effort"] == "low"


def test_from_env_points_at_meta(monkeypatch):
    created = {}

    class FakeOpenAI:
        def __init__(self, base_url, api_key):
            created["base_url"] = base_url
            created["api_key"] = api_key

    monkeypatch.setenv("META_API_KEY", "LLM_test_secret")
    monkeypatch.setattr("kalkan.providers.meta.OpenAI", FakeOpenAI, raising=False)
    # OpenAI is imported inside from_env, so patch the sdk module if it exists
    # and also the name lookup by injecting before the local import.
    import openai

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    provider = MetaProvider.from_env()
    assert created["base_url"] == META_BASE_URL
    assert created["api_key"] == "LLM_test_secret"
    assert provider.mode == "meta"


def test_auto_provider_stays_mock_without_a_key(monkeypatch, tmp_path):
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.setenv("KALKAN_PROVIDER", "auto")
    monkeypatch.setenv("KALKAN_DATA_DIR", str(tmp_path))
    settings = load_settings()
    assert settings.provider == "mock"


def test_meta_mode_without_a_key_fails(monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.setenv("KALKAN_PROVIDER", "meta")
    with pytest.raises(ConfigError):
        load_settings()


def test_mock_refuses_contributor_id():
    provider = MockProvider()
    with pytest.raises(ConfigError):
        provider.complete_json(
            model="muse-spark-1.3-contributor",
            messages=[{"role": "user", "content": "KALKAN_PAYLOAD {}"}],
            schema_name="kalkan_verdict",
            schema={},
            reasoning_effort="low",
        )
