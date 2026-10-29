"""Runtime configuration. Secrets stay in the environment and are never logged."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

STANDARD_MODELS = frozenset(
    {
        "muse-wonder-1.0",
        "muse-spark-1.3",
        "muse-spark-1.2",
        "muse-spark-1.1",
    }
)

DEFAULT_SPARK = "muse-spark-1.3"
DEFAULT_WONDER = "muse-wonder-1.0"
DEFAULT_PROMPT_GUARD = "meta-llama/Llama-Prompt-Guard-2-86M"


class ConfigError(RuntimeError):
    pass


def api_key() -> str:
    """Meta Model API key. META_API_KEY wins; MODEL_API_KEY is Meta's own name."""
    return os.environ.get("META_API_KEY", "").strip() or os.environ.get("MODEL_API_KEY", "").strip()


def assert_standard_model(model: str) -> str:
    if "contributor" in model.lower():
        raise ConfigError(
            f"Refusing model {model!r}. Kalkan only calls Standard mode. "
            "Contributor model IDs let Meta train on the content, which is wrong "
            "for untrusted mail and security decisions."
        )
    if model not in STANDARD_MODELS:
        allowed = ", ".join(sorted(STANDARD_MODELS))
        raise ConfigError(f"Refusing model {model!r}. Allowed Standard IDs: {allowed}.")
    return model


def find_root() -> Path:
    override = os.environ.get("KALKAN_ROOT", "").strip()
    if override:
        return Path(override)
    here = Path(__file__).resolve()
    candidates = [Path.cwd(), *here.parents]
    for candidate in candidates:
        if (candidate / "policy" / "default.yaml").is_file() and (candidate / "evals").is_dir():
            return candidate
    return Path.cwd()


@dataclass(frozen=True)
class Settings:
    root: Path
    provider: str
    screen: str
    spark_model: str
    wonder_model: str
    prompt_guard_model: str
    data_dir: Path
    host: str
    port: int

    @property
    def meta_api_key_set(self) -> bool:
        return bool(api_key())


def load_settings() -> Settings:
    root = find_root()
    provider = os.environ.get("KALKAN_PROVIDER", "auto").strip().lower() or "auto"
    screen = os.environ.get("KALKAN_SCREEN", "auto").strip().lower() or "auto"
    if provider not in {"auto", "mock", "meta"}:
        raise ConfigError("KALKAN_PROVIDER must be auto, mock, or meta.")
    if screen not in {"auto", "heuristic", "prompt-guard"}:
        raise ConfigError("KALKAN_SCREEN must be auto, heuristic, or prompt-guard.")
    if provider == "auto":
        provider = "meta" if api_key() else "mock"
    if provider == "meta" and not api_key():
        raise ConfigError(
            "KALKAN_PROVIDER=meta but neither META_API_KEY nor MODEL_API_KEY is set."
        )
    spark = assert_standard_model(os.environ.get("KALKAN_SPARK_MODEL", DEFAULT_SPARK).strip())
    wonder = assert_standard_model(os.environ.get("KALKAN_WONDER_MODEL", DEFAULT_WONDER).strip())
    data_dir = Path(os.environ.get("KALKAN_DATA_DIR", str(root / "data")))
    host = os.environ.get("KALKAN_HOST", "0.0.0.0")
    port = int(os.environ.get("KALKAN_PORT", "8080"))
    return Settings(
        root=root,
        provider=provider,
        screen=screen,
        spark_model=spark,
        wonder_model=wonder,
        prompt_guard_model=os.environ.get("KALKAN_PROMPT_GUARD_MODEL", DEFAULT_PROMPT_GUARD).strip(),
        data_dir=data_dir,
        host=host,
        port=port,
    )
