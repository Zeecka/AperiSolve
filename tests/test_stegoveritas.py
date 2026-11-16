"""Tests for the partial StegoVeritas analyzers and their driver (docker/stegoveritas_driver.py).

The wrapper tests mock the subprocess and run anywhere. The driver tests need
the stegoveritas packages (the isolated venv of the image, or a local venv with
``docker/stegoveritas-requirements.txt``) and are skipped otherwise.
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from subprocess import CompletedProcess
from types import ModuleType

import numpy as np
import pytest
from PIL import Image

from aperisolve.analyzers import stegoveritas
from aperisolve.analyzers.base_analyzer import SubprocessAnalyzer
from aperisolve.analyzers.pil_utils import MAX_IMAGE_PIXELS, PALETTE_NOTE
from aperisolve.analyzers.stegoveritas import StegoveritasAnalyzer

DRIVER_PATH = Path(__file__).resolve().parent.parent / "docker" / "stegoveritas_driver.py"
BIT_PLANE_RE = re.compile(r"_(Red|Green|Blue|Alpha)_[0-9]")


def _fake_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, **kwargs: object) -> list[list[str]]:
    """Mock ``run_command``; return the list that records the argv it receives."""
    venv_python = tmp_path / "python"
    driver = tmp_path / "driver.py"
    venv_python.touch()
    driver.touch()
    monkeypatch.setattr(stegoveritas, "VENV_PYTHON", venv_python)
    monkeypatch.setattr(stegoveritas, "DRIVER", driver)
    calls: list[list[str]] = []

    def run_command(
        _self: object,
        cmd: list[str],
        cwd: Path | None = None,
    ) -> CompletedProcess[str]:
        _ = cwd
        calls.append(cmd)
        return CompletedProcess(cmd, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(SubprocessAnalyzer, "run_command", run_command)
    return calls


def _run(tmp_path: Path) -> dict:
    out = tmp_path / "sub"
    out.mkdir()
    return StegoveritasAnalyzer(tmp_path / "img.png", out).get_results()


def test_wrapper_turns_driver_names_into_image_urls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Names printed by the driver become /image/<submission>/<name> URLs; no regex, no copy."""
    payload = {"status": "ok", "images": {"Transforms": ["stegoveritas_a.png"]}, "skipped": []}
    calls = _fake_run(monkeypatch, tmp_path, returncode=0, stdout=json.dumps(payload), stderr="")
    result = _run(tmp_path)
    assert result["status"] == "ok"
    assert result["images"] == {"Transforms": ["/image/sub/stegoveritas_a.png"]}
    assert "download" not in result
    assert "note" not in result
    argv = calls[0]
    assert argv[1:3] == ["-I", str(tmp_path / "driver.py")]
    assert argv[3:] == [
        "transforms",
        str(tmp_path / "img.png"),
        str(tmp_path / "sub"),
        str(MAX_IMAGE_PIXELS),
    ]


def test_wrapper_notes_palette_and_skipped_ops(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A palette conversion and the ops Pillow refused are reported, not hidden."""
    payload = {
        "status": "ok",
        "images": {"Transforms": ["stegoveritas_a.png"]},
        "palette": True,
        "skipped": ["equalize.png"],
    }
    _fake_run(monkeypatch, tmp_path, returncode=0, stdout=json.dumps(payload), stderr="")
    note = _run(tmp_path)["note"]
    assert PALETTE_NOTE in note
    assert "equalize.png" in note


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {"returncode": 0, "stdout": "not json", "stderr": ""},
            "stegoveritas produced invalid output",
        ),
        (
            {
                "returncode": 1,
                "stdout": "",
                "stderr": "Traceback (most recent call last):\nOSError: bad\n",
            },
            "OSError: bad",
        ),
        (
            {
                "returncode": 0,
                "stdout": json.dumps({"status": "error", "error": "too big"}),
                "stderr": "",
            },
            "too big",
        ),
    ],
)
def test_wrapper_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kwargs: dict,
    expected: str,
) -> None:
    """Bad JSON, a crash (last traceback line only) and a driver error all become error results."""
    _fake_run(monkeypatch, tmp_path, **kwargs)
    assert _run(tmp_path) == {"status": "error", "error": expected}


def test_wrapper_reports_missing_venv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Dev hosts without the image's venv get a clear error instead of a crash."""
    monkeypatch.setattr(stegoveritas, "VENV_PYTHON", tmp_path / "absent")
    assert _run(tmp_path) == {"status": "error", "error": "stegoveritas is not installed"}


# ---------------------------------------------------------------------------
# Driver (needs the stegoveritas packages)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def driver() -> ModuleType:
    """Import docker/stegoveritas_driver.py, or skip when stegoveritas is not installed."""
    pytest.importorskip("stegoveritas.modules.image.analysis.filters")
    pytest.importorskip("apng")
    spec = importlib.util.spec_from_file_location("stegoveritas_driver", DRIVER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _noise(mode: str, size: tuple[int, int] = (24, 32)) -> Image.Image:
    rng = np.random.default_rng(0)
    channels = {"L": 1, "RGB": 3, "RGBA": 4}[mode]
    shape = size[::-1] if channels == 1 else (*size[::-1], channels)
    return Image.fromarray(rng.integers(0, 256, shape, dtype=np.uint8), mode)


@pytest.mark.parametrize("mode", ["L", "RGB", "RGBA", "P"])
def test_driver_transforms_every_mode_without_bit_planes(
    driver: ModuleType,
    tmp_path: Path,
    mode: str,
) -> None:
    """Palette images are transformed too; bit planes are never produced."""
    src = tmp_path / "in.png"
    (_noise("RGB").convert("P") if mode == "P" else _noise(mode)).save(src)
    out = tmp_path / "out"
    out.mkdir()
    result = driver.transforms(src, out, 1_000_000)
    names = result["images"]["Transforms"]
    assert result["status"] == "ok"
    assert len(names) >= 14
    assert sorted(p.name for p in out.iterdir()) == names
    assert all(name.startswith("stegoveritas_") for name in names)
    assert not any(BIT_PLANE_RE.search(name) for name in names)
    assert result["palette"] is (mode == "P")
    # Colour planes need three bands: none for grayscale.
    assert any("red_plane" in n for n in names) is (mode != "L")


def test_driver_skips_ops_pillow_refuses_instead_of_crashing(
    driver: ModuleType,
    tmp_path: Path,
) -> None:
    """Pillow 13 raises OSError for ImageOps on RGBA; the op is skipped and reported."""
    src = tmp_path / "in.png"
    _noise("RGBA").save(src)
    out = tmp_path / "out"
    out.mkdir()
    result = driver.transforms(src, out, 1_000_000)
    assert result["status"] == "ok"
    assert "autocontrast.png" in result["skipped"]
    assert "stegoveritas_grayscale.png" in result["images"]["Transforms"]


def test_driver_refuses_oversized_image_before_decoding(driver: ModuleType, tmp_path: Path) -> None:
    """The megapixel limit is read from the header, with the text of ``load_image_array``."""
    src = tmp_path / "big.png"
    Image.new("RGB", (4000, 4000)).save(src)
    out = tmp_path / "out"
    out.mkdir()
    result = driver.transforms(src, out, 8_000_000)
    assert result == {
        "status": "error",
        "error": "Image dimensions 4000x4000 exceed the 8 megapixel processing limit.",
    }
    assert list(out.iterdir()) == []


def test_driver_undecodable_input_is_an_error_result(driver: ModuleType, tmp_path: Path) -> None:
    """Corrupt uploads are expected input: an error result, not a traceback."""
    src = tmp_path / "bad.png"
    src.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    out = tmp_path / "out"
    out.mkdir()
    assert driver.transforms(src, out, 1_000_000)["status"] == "error"


def _animation(path: Path, fmt: str, count: int) -> None:
    frames = [Image.new("RGB", (8, 8), (i * 20 % 256, 0, 0)) for i in range(count)]
    frames[0].save(path, format=fmt, save_all=True, append_images=frames[1:])


@pytest.mark.parametrize(("fmt", "ext"), [("GIF", "gif"), ("PNG", "png")])
def test_driver_extracts_every_frame_in_order(
    driver: ModuleType,
    tmp_path: Path,
    fmt: str,
    ext: str,
) -> None:
    """Frames come back as a name list , no filename regex in the caller."""
    src = tmp_path / f"anim.{ext}"
    _animation(src, fmt, 12)
    out = tmp_path / "out"
    out.mkdir()
    result = driver.frames(src, out, 1_000_000, 100)
    names = result["images"]["Frames"]
    assert [int(re.search(r"_frame_(\d+)\.", n).group(1)) for n in names] == list(range(12))
    assert all((out / n).is_file() for n in names)
    assert len(list((out / "stegoveritas_frames").iterdir())) == 12


@pytest.mark.parametrize(("fmt", "ext"), [("GIF", "gif"), ("PNG", "png")])
def test_driver_frame_cap_is_loud_and_extracts_nothing(
    driver: ModuleType,
    tmp_path: Path,
    fmt: str,
    ext: str,
) -> None:
    """101 frames: an error naming the 100-frame limit, before any frame is written."""
    src = tmp_path / f"anim.{ext}"
    _animation(src, fmt, 101)
    out = tmp_path / "out"
    out.mkdir()
    result = driver.frames(src, out, 1_000_000, 100)
    assert result["status"] == "error"
    assert "100-frame limit" in result["error"]
    assert list(out.iterdir()) == []


def test_driver_frames_of_a_still_image_is_empty(driver: ModuleType, tmp_path: Path) -> None:
    """Defence in depth: the animated gate normally keeps stills away from this mode."""
    src = tmp_path / "still.png"
    _noise("RGB").save(src)
    out = tmp_path / "out"
    out.mkdir()
    assert driver.frames(src, out, 1_000_000, 100) == {"status": "ok", "images": {}}


def test_driver_selftest(driver: ModuleType) -> None:
    """The build-time self-test of the Dockerfile passes in this environment too."""
    driver._selftest()  # noqa: SLF001


def _venv_python() -> Path | None:
    """First interpreter that imports stegoveritas under ``-I`` (the driver's own flags)."""
    candidates = [stegoveritas.VENV_PYTHON, Path(sys.executable)]
    if os.environ.get("STEGOVERITAS_PYTHON"):
        candidates.insert(0, Path(os.environ["STEGOVERITAS_PYTHON"]))
    for python in candidates:
        probe = [str(python), "-I", "-c", "import stegoveritas.modules.image.analysis.filters"]
        try:
            if subprocess.run(probe, capture_output=True, check=False).returncode == 0:  # noqa: S603
                return python
        except OSError:
            continue
    return None


def test_analyzer_end_to_end_with_the_real_driver(
    driver: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Wrapper + subprocess + driver: stdout stays pure JSON and results.json gets the images."""
    _ = driver
    python = _venv_python()
    if python is None:
        pytest.skip("no isolated stegoveritas interpreter (set STEGOVERITAS_PYTHON)")
    monkeypatch.setattr(stegoveritas, "VENV_PYTHON", python)
    monkeypatch.setattr(stegoveritas, "DRIVER", DRIVER_PATH)
    src = tmp_path / "in.png"
    _noise("RGB").save(src)
    out = tmp_path / "sub"
    out.mkdir()
    StegoveritasAnalyzer.execute(src, out)
    entry = json.loads((out / "results.json").read_text(encoding="utf-8"))["stegoveritas"]
    assert entry["status"] == "ok"
    assert len(entry["images"]["Transforms"]) >= 14
    assert "download" not in entry
    assert not (out / "stegoveritas.7z").exists()
