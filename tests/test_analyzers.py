"""Smoke tests running cheap analyzers against a fixture image."""

import json
import shutil
from pathlib import Path

import pytest

from aperisolve.analyzers.decomposer import DecomposerAnalyzer
from aperisolve.analyzers.file import FileAnalyzer
from aperisolve.analyzers.strings import StringsAnalyzer

EXAMPLE_IMAGE = Path(__file__).resolve().parent.parent / "examples" / "example1.png"


def _read_results(output_dir: Path) -> dict:
    return json.loads((output_dir / "results.json").read_text(encoding="utf-8"))


def test_decomposer_produces_bit_planes(tmp_path: Path) -> None:
    """The pure-Python decomposer runs anywhere and emits images."""
    DecomposerAnalyzer.execute(EXAMPLE_IMAGE, tmp_path)
    results = _read_results(tmp_path)
    assert results["decomposer"]["status"] == "ok"
    assert results["decomposer"]["images"]


@pytest.mark.skipif(shutil.which("file") is None, reason="file binary not installed")
def test_file_identifies_png(tmp_path: Path) -> None:
    """The `file` analyzer identifies the fixture as a PNG."""
    output_dir = tmp_path / EXAMPLE_IMAGE.stem
    output_dir.mkdir()
    shutil.copy(EXAMPLE_IMAGE, tmp_path / EXAMPLE_IMAGE.name)
    FileAnalyzer.execute(tmp_path / EXAMPLE_IMAGE.name, output_dir)
    results = _read_results(output_dir)
    assert results["file"]["status"] == "ok"
    assert "PNG" in results["file"]["output"]


@pytest.mark.skipif(shutil.which("strings") is None, reason="strings binary not installed")
def test_strings_extracts_text(tmp_path: Path) -> None:
    """The strings analyzer returns lines without error."""
    output_dir = tmp_path / EXAMPLE_IMAGE.stem
    output_dir.mkdir()
    shutil.copy(EXAMPLE_IMAGE, tmp_path / EXAMPLE_IMAGE.name)
    StringsAnalyzer.execute(tmp_path / EXAMPLE_IMAGE.name, output_dir)
    results = _read_results(output_dir)
    assert results["strings"]["status"] == "ok"
    assert isinstance(results["strings"]["output"], list)
