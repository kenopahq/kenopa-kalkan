"""Construct the model provider selected by settings."""

from __future__ import annotations

from kalkan.config import Settings
from kalkan.providers.meta import MetaProvider
from kalkan.providers.mock import MockProvider


def build_provider(settings: Settings):
    if settings.provider == "meta":
        return MetaProvider.from_env()
    return MockProvider()


__all__ = ["MetaProvider", "MockProvider", "build_provider"]
