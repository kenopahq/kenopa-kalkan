"""Pass 1 screen factory."""

from __future__ import annotations

from kalkan.config import Settings
from kalkan.screen.base import Screen
from kalkan.screen.heuristic import HeuristicScreen, Pattern, load_patterns
from kalkan.screen.prompt_guard import PromptGuardError, PromptGuardScreen


def build_screen(settings: Settings) -> Screen:
    if settings.screen == "prompt-guard":
        return PromptGuardScreen.from_pretrained(settings.prompt_guard_model)
    patterns = load_patterns(settings.root / "policy" / "screen_patterns.yaml")
    note = (
        "Offline heuristic. This is not Llama Prompt Guard 2. "
        "Set KALKAN_SCREEN=prompt-guard after accepting the Hugging Face gate "
        "to load meta-llama/Llama-Prompt-Guard-2-86M."
    )
    return HeuristicScreen(patterns, backend_note=note)


__all__ = [
    "HeuristicScreen",
    "Pattern",
    "PromptGuardError",
    "PromptGuardScreen",
    "Screen",
    "build_screen",
    "load_patterns",
]
