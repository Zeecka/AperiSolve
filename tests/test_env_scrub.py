"""An analyzer subprocess must not inherit the worker's secrets (ZEL-442)."""

import shutil
from pathlib import Path

import pytest

from aperisolve.analyzers.base_analyzer import SubprocessAnalyzer


@pytest.mark.skipif(shutil.which("env") is None, reason="env binary not installed")
def test_subprocess_does_not_see_worker_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A secret set in the worker's own environment must not reach a child."""
    monkeypatch.setenv("DB_URI", "postgresql://aperiuser:supersecret@postgres:5432/aperisolve")
    monkeypatch.setenv("REDIS_URL", "redis://:supersecret@redis:6379/0")

    analyzer = SubprocessAnalyzer(tmp_path / "img.png", tmp_path)
    result = analyzer.run_command(["env"])

    assert "DB_URI" not in result.stdout
    assert "REDIS_URL" not in result.stdout
    assert "supersecret" not in result.stdout


@pytest.mark.skipif(shutil.which("env") is None, reason="env binary not installed")
def test_subprocess_env_is_the_fixed_minimal_set(tmp_path: Path) -> None:
    """Only PATH, HOME and LANG reach the subprocess -- nothing ambient."""
    analyzer = SubprocessAnalyzer(tmp_path / "img.png", tmp_path)
    result = analyzer.run_command(["env"])

    seen = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    assert set(seen) == {"PATH", "HOME", "LANG"}
    assert seen["HOME"] == "/tmp"  # noqa: S108 -- asserting the fixed sandbox HOME, not using it
    assert seen["LANG"] == "C.UTF-8"
