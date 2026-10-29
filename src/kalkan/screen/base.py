"""Screen interface."""

from __future__ import annotations

from typing import Protocol

from kalkan.models import ScreenResult


class Screen(Protocol):
    backend: str

    def scan(self, text: str) -> ScreenResult:
        """Label text MALICIOUS or BENIGN."""
