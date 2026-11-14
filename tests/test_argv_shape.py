"""Argv-shape regression tests for every ``needs_password`` analyzer (ZEL-442).

A hostile password or filename must always land as exactly one argv element,
directly after the flag that carries it (``-p``/``-k``, or as a single
``JPSEEK_PASS=`` environment assignment for jpseek) -- never split, never
shell-interpolated. ``run_command``/``create_subprocess_exec`` already make
that true by construction (no shell involved); these tests pin the invariant
so a future refactor toward string formatting or ``shell=True`` fails loudly.
"""

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from aperisolve.analyzers.jpseek import JpseekAnalyzer
from aperisolve.analyzers.openstego import OpenStegoAnalyzer
from aperisolve.analyzers.outguess import OutguessAnalyzer
from aperisolve.analyzers.steghide import SteghideAnalyzer

HOSTILE_STRINGS = ["-xf", "--", ";", "$(id)", "line1\nline2", "}"]


@pytest.mark.parametrize("hostile", HOSTILE_STRINGS)
def test_outguess_password_is_single_argv_element(tmp_path: Path, hostile: str) -> None:
    """Outguess receives the password as one element directly after -k."""
    analyzer = OutguessAnalyzer(tmp_path / "img.jpg", tmp_path / "out")
    cmd = analyzer.build_cmd(hostile)
    assert cmd[cmd.index("-k") + 1] == hostile
    assert cmd.count(hostile) == 1


@pytest.mark.parametrize("hostile", HOSTILE_STRINGS)
def test_outguess_filename_is_single_argv_element(tmp_path: Path, hostile: str) -> None:
    """A hostile stored filename stays one argv element, not shell-expanded."""
    name = f"abc.jpg{hostile}"
    analyzer = OutguessAnalyzer(tmp_path / name, tmp_path / "out")
    cmd = analyzer.build_cmd("pw")
    assert f"../{name}" in cmd
    assert cmd.count(f"../{name}") == 1


@pytest.mark.parametrize("hostile", HOSTILE_STRINGS)
def test_openstego_password_is_single_argv_element(tmp_path: Path, hostile: str) -> None:
    """Openstego receives the password as one element directly after -p."""
    analyzer = OpenStegoAnalyzer(tmp_path / "img.png", tmp_path / "out")
    cmd = analyzer.build_cmd(hostile)
    assert cmd[cmd.index("-p") + 1] == hostile
    assert cmd.count(hostile) == 1


@pytest.mark.parametrize("hostile", HOSTILE_STRINGS)
def test_openstego_filename_is_single_argv_element(tmp_path: Path, hostile: str) -> None:
    """A hostile stored filename stays one argv element, not shell-expanded."""
    name = f"abc.png{hostile}"
    analyzer = OpenStegoAnalyzer(tmp_path / name, tmp_path / "out")
    cmd = analyzer.build_cmd("pw")
    assert f"../{name}" in cmd
    assert cmd.count(f"../{name}") == 1


@pytest.mark.parametrize("hostile", HOSTILE_STRINGS)
def test_steghide_password_is_single_argv_element(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hostile: str,
) -> None:
    """Steghide receives the password as one element directly after -p.

    build_cmd probes with a real steghide subprocess first (to look up the
    embedded filename); force that probe to "fail" so the test exercises the
    argv shape without needing the steghide binary installed.
    """
    analyzer = SteghideAnalyzer(tmp_path / "img.jpg", tmp_path / "out")
    monkeypatch.setattr(
        analyzer,
        "run_command",
        lambda *a, **k: CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),  # noqa: ARG005
    )
    cmd = analyzer.build_cmd(hostile)
    assert cmd[cmd.index("-p") + 1] == hostile
    assert cmd.count(hostile) == 1


@pytest.mark.parametrize("hostile", HOSTILE_STRINGS)
def test_steghide_filename_is_single_argv_element(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hostile: str,
) -> None:
    """A hostile stored filename stays one argv element, not shell-expanded."""
    name = f"abc.jpg{hostile}"
    analyzer = SteghideAnalyzer(tmp_path / name, tmp_path / "out")
    monkeypatch.setattr(
        analyzer,
        "run_command",
        lambda *a, **k: CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),  # noqa: ARG005
    )
    cmd = analyzer.build_cmd("pw")
    assert f"../{name}" in cmd
    assert cmd.count(f"../{name}") == 1


@pytest.mark.parametrize("hostile", HOSTILE_STRINGS)
def test_jpseek_password_is_single_env_assignment(tmp_path: Path, hostile: str) -> None:
    """Jpseek receives the password as one JPSEEK_PASS= environment argv element."""
    analyzer = JpseekAnalyzer(tmp_path / "img.jpg", tmp_path / "out")
    cmd = analyzer.build_cmd(hostile)
    assert cmd.count(f"JPSEEK_PASS={hostile}") == 1
