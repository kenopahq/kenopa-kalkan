import pytest

from kalkan.runtime import build_runtime


@pytest.fixture()
def runtime(tmp_path, monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.setenv("KALKAN_PROVIDER", "mock")
    monkeypatch.setenv("KALKAN_SCREEN", "heuristic")
    monkeypatch.setenv("KALKAN_DATA_DIR", str(tmp_path))
    return build_runtime()
