"""Regression test for GHSA-m5f8-qc9j-mc55 (Tcl injection via JPSeek paths)."""

from pathlib import Path

from aperisolve.analyzers.jpseek import JpseekAnalyzer


def test_jpseek_paths_are_not_interpolated_into_tcl(tmp_path: Path) -> None:
    """A hostile stored image path only travels through environment variables."""
    name = "abc.jpg}; exec sh -c {id>p}; #"
    analyzer = JpseekAnalyzer(tmp_path / name, tmp_path / "out")

    cmd = analyzer.build_cmd("pw}; exec id; #")

    script = cmd[cmd.index("-c") + 1]
    assert name not in script
    assert "pw" not in script
    assert script.startswith("spawn jpseek $env(JPSEEK_IMG) $env(JPSEEK_OUT);")
    assert f"JPSEEK_IMG=../{name}" in cmd
