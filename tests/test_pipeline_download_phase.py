"""Tests for MediaPipeline download phase toggle behaviour"""

from pathlib import Path
import sys
from typing import List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from run_pipeline import MediaPipeline, PhaseStatus


def _set_toggle(monkeypatch: pytest.MonkeyPatch, name: str, value: bool) -> None:
    monkeypatch.setenv(name, "true" if value else "false")


def test_download_phase_enabled_when_any_source_toggle_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Download phase should run when folder download is enabled."""
    _set_toggle(monkeypatch, "ENABLE_ICLOUD_DOWNLOAD", False)
    _set_toggle(monkeypatch, "ENABLE_FOLDER_DOWNLOAD", True)

    pipeline = MediaPipeline()

    assert pipeline._is_download_phase_enabled() is True


def test_run_phase_uses_callable_toggle_for_download(monkeypatch: pytest.MonkeyPatch) -> None:
    """Callable toggle entries should execute the phase when returning True."""
    _set_toggle(monkeypatch, "ENABLE_ICLOUD_DOWNLOAD", False)
    _set_toggle(monkeypatch, "ENABLE_FOLDER_DOWNLOAD", True)

    pipeline = MediaPipeline()

    calls: List[bool] = []

    def fake_phase() -> bool:
        calls.append(True)
        return True

    result = pipeline.run_phase("download", pipeline.phases[0][1], fake_phase)

    assert result.status is PhaseStatus.SUCCESS
    assert calls == [True]


def test_run_phase_skips_when_callable_toggle_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Callable toggle returning False should skip phase execution."""
    _set_toggle(monkeypatch, "ENABLE_ICLOUD_DOWNLOAD", False)
    _set_toggle(monkeypatch, "ENABLE_FOLDER_DOWNLOAD", False)

    pipeline = MediaPipeline()

    def failing_phase() -> bool:  # pragma: no cover - should not run
        raise AssertionError("Phase should not execute when toggle is False")

    result = pipeline.run_phase("download", lambda: False, failing_phase)

    assert result.status is PhaseStatus.DISABLED
