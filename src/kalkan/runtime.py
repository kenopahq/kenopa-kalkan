"""Wire the policy, screen, judge, and sandbox into one runtime."""

from __future__ import annotations

from dataclasses import dataclass

from kalkan.agent.sandbox import Sandbox, load_sandbox
from kalkan.config import Settings, load_settings
from kalkan.firewall import Firewall
from kalkan.judge.spark import SparkJudge
from kalkan.policy import Policy, load_policy
from kalkan.providers import build_provider
from kalkan.screen import build_screen
from kalkan.store import EventLog


@dataclass
class Runtime:
    settings: Settings
    policy: Policy
    screen: object
    provider: object
    judge: SparkJudge
    firewall: Firewall
    sandbox: Sandbox
    events: EventLog

    def status(self) -> dict:
        screen_backend = getattr(self.screen, "backend", "unknown")
        return {
            "provider": self.provider.mode,
            "judge_backend": self.judge.backend,
            "screen_backend": screen_backend,
            "screen_note": getattr(self.screen, "backend_note", ""),
            "spark_model": self.settings.spark_model,
            "wonder_model": self.settings.wonder_model,
            "prompt_guard_model": self.settings.prompt_guard_model,
            "meta_api_key_set": self.settings.meta_api_key_set,
            "prompt_guard_weights_loaded": screen_backend == "llama-prompt-guard-2-86m",
            "standard_models_only": True,
            "version": "0.1.0",
        }


def build_runtime(settings: Settings | None = None) -> Runtime:
    settings = settings or load_settings()
    policy = load_policy(settings.root / "policy" / "default.yaml")
    screen = build_screen(settings)
    provider = build_provider(settings)
    judge = SparkJudge(provider, policy, settings.spark_model)
    firewall = Firewall(screen, judge, policy)
    sandbox = load_sandbox(settings.root)
    events = EventLog(settings.data_dir / "events.jsonl")
    return Runtime(
        settings=settings,
        policy=policy,
        screen=screen,
        provider=provider,
        judge=judge,
        firewall=firewall,
        sandbox=sandbox,
        events=events,
    )
