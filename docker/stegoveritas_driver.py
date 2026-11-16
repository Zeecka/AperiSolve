"""Partial StegoVeritas driver: image transforms and animated-frame extraction.

Runs inside /opt/stegoveritas-venv (stegoveritas + pillow + numpy + apng only;
no aperisolve import). It calls StegoVeritas' per-operation functions one by
one, in one process, and never its CLI: ``filters.run()`` would also compute
every bit plane (the decomposer already does) in an unbounded process pool,
and ``StegoVeritas()`` would re-run brute-LSB, carve, steghide, exif and xmp.

    driver.py transforms <image> <out_dir> <max_pixels>
    driver.py frames     <image> <out_dir> <max_pixels> <max_frames>
    driver.py --selftest

Prints ``{"status", "images": {group: [names]}, "palette", "skipped"}`` (or
``{"status": "error", "error"}``) as JSON on stdout. Everything the library
prints goes to stderr so stdout stays parseable.
"""

import contextlib
import json
import os
import re
import shutil
import struct
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from stegoveritas.modules.image.analysis import extract_frames, filters

PREFIX = "stegoveritas"
FRAMES_DIR = f"{PREFIX}_frames"
_FRAME_NUM = re.compile(r"_frame_(\d+)\.")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_RGB_BANDS = 3

# ModeFilter (slowest, ~Median) and the 6 weaker sharpness levels are dropped.
_FILTERS = (
    ImageFilter.EDGE_ENHANCE,
    ImageFilter.EDGE_ENHANCE_MORE,
    ImageFilter.FIND_EDGES,
    ImageFilter.MaxFilter,
    ImageFilter.MedianFilter,
    ImageFilter.MinFilter,
    ImageFilter.SHARPEN,
    ImageFilter.SMOOTH,
    ImageFilter.GaussianBlur,
)
_ENHANCERS = (
    ([(ImageEnhance.Sharpness, 100)], "enhance_sharpness_100.png"),
    ([(ImageEnhance.Sharpness, -100)], "enhance_sharpness_-100.png"),
)
_IMAGE_OPS = (
    (ImageOps.autocontrast, "autocontrast.png"),
    (ImageOps.grayscale, "grayscale.png"),
    (ImageOps.equalize, "equalize.png"),
    (ImageOps.invert, "inverted.png"),
    (ImageOps.solarize, "solarized.png"),
)


def _error(message: str) -> dict[str, Any]:
    return {"status": "error", "error": message}


def _too_big(img: Image.Image, max_pixels: int) -> dict[str, Any] | None:
    """Same refusal, from the header alone, as ``pil_utils.load_image_array``."""
    if img.width * img.height > max_pixels:
        return _error(
            f"Image dimensions {img.width}x{img.height} exceed the "
            f"{max_pixels // 1_000_000} megapixel processing limit.",
        )
    return None


def _open_error(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, Image.DecompressionBombError):
        return _error("Image rejected: decoded size would be a decompression bomb.")
    return _error(f"Pillow cannot decode the image data: {exc}")


def _png_frame_count(path: Path) -> int:
    """Count ``fcTL`` chunks from the chunk headers (``acTL`` can lie, and APNG reads them all)."""
    count = 0
    with path.open("rb") as f:
        if f.read(8) != _PNG_SIGNATURE:
            return 0
        while header := f.read(8):
            if len(header) < 8:
                break
            length, kind = struct.unpack(">I4s", header)
            count += kind == b"fcTL"
            f.seek(length + 4, os.SEEK_CUR)
    return count


def _normalize(img: Image.Image) -> tuple[Image.Image, bool]:
    """Return an L/RGB/RGBA copy of ``img`` and whether it was a palette image."""
    palette = img.mode == "P"
    if img.mode in {"L", "RGB", "RGBA"}:
        return img, False
    has_alpha = "A" in img.getbands() or "transparency" in img.info
    if img.mode in {"1", "I", "F"} or img.mode.startswith("I;"):
        return img.convert("L"), False
    return img.convert("RGBA" if has_alpha else "RGB"), palette


def transforms(path: Path, out: Path, max_pixels: int) -> dict[str, Any]:
    """Write the filters, colour planes, enhancers and image ops into ``out``."""
    try:
        with Image.open(path) as opened:
            if (refused := _too_big(opened, max_pixels)) is not None:
                return refused
            img, palette = _normalize(opened)
            img.load()
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        return _open_error(exc)

    # Other analyzers write into ``out`` at the same time, so the files are produced in a
    # private folder and moved over: the names reported are exactly ours.
    # The upstream functions only read ``.file`` and ``.veritas.{results_directory,file_name}``;
    # the file name is the output prefix.
    scratch = Path(tempfile.mkdtemp(prefix=f".{PREFIX}-", dir=out))
    image = SimpleNamespace(
        file=img,
        veritas=SimpleNamespace(results_directory=str(scratch), file_name=PREFIX),
    )
    bands = img.getbands()
    # Same trick as upstream: the filters work on the image with a fully opaque alpha.
    flat = img
    if "A" in bands:
        arr = numpy.array(img)
        arr[:, :, bands.index("A")] = 0xFF
        flat = Image.fromarray(arr)

    ops: list[tuple[str, Any]] = [(f.name, lambda f=f: filters.run_filter(image, flat, f)) for f in _FILTERS]
    if len(bands) >= _RGB_BANDS:
        ops += [
            (f"{p} plane", lambda p=p: filters.run_color_planes(image, flat, p))
            for p in ("red", "green", "blue", "alpha")
        ]
    ops += [(n, lambda e=e, n=n: filters.run_enhancer(image, e, n)) for e, n in _ENHANCERS]
    ops += [(n, lambda o=o, n=n: filters.run_image_op(image, o, n)) for o, n in _IMAGE_OPS]

    skipped: list[str] = []
    with contextlib.redirect_stdout(sys.stderr):
        for name, op in ops:
            try:
                op()
            except OSError as exc:  # Pillow refuses some ops on some modes (e.g. RGBA)
                print(f"{name}: {exc}", file=sys.stderr)
                skipped.append(name)
    names = sorted(os.listdir(scratch))
    for name in names:
        (scratch / name).replace(out / name)
    scratch.rmdir()
    return {"status": "ok", "images": {"Transforms": names}, "palette": palette, "skipped": skipped}


def frames(path: Path, out: Path, max_pixels: int, max_frames: int) -> dict[str, Any]:
    """Extract the frames of an animated GIF/APNG into ``out/stegoveritas_frames``."""
    try:
        with Image.open(path) as img:
            if (refused := _too_big(img, max_pixels)) is not None:
                return refused
            kind = img.format
            count = _png_frame_count(path) if kind == "PNG" else getattr(img, "n_frames", 1)
            if count > max_frames:
                return _error(f"{count} frames exceed the {max_frames}-frame limit.")
            if count < 2:
                return {"status": "ok", "images": {}}
            target = out / FRAMES_DIR
            target.mkdir(exist_ok=True)
            image = SimpleNamespace(
                file=img,
                veritas=SimpleNamespace(
                    results_directory=str(target),
                    file_name=str(path),
                    args=SimpleNamespace(auto=False, extract_frames=True),
                ),
            )
            with contextlib.redirect_stdout(sys.stderr):
                extract_frames.run(image)
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        return _open_error(exc)

    # Hard-link each frame next to the results.json so the page can serve it; the
    # directory itself is zipped and removed by the analyzer.
    names = []
    for frame in sorted(target.iterdir(), key=lambda p: int(_FRAME_NUM.search(p.name).group(1))):
        link = out / f"{FRAMES_DIR}_{frame.name}"
        try:
            os.link(frame, link)
        except OSError:
            shutil.copy2(frame, link)
        names.append(link.name)
    return {"status": "ok", "images": {"Frames": names}}


def _selftest() -> None:
    """Run every mode on tiny inputs; fail loudly if stegoveritas or Pillow moved under us."""
    rng = numpy.random.default_rng(0)
    noise = rng.integers(0, 256, (32, 48, 4), dtype=numpy.uint8)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        inputs = {
            "rgb": Image.fromarray(noise[:, :, :3]),
            "rgba": Image.fromarray(noise),
            "gray": Image.fromarray(noise[:, :, 0]),
            "palette": Image.fromarray(noise[:, :, :3]).convert("P"),
        }
        for label, img in inputs.items():
            src = root / f"{label}.png"
            img.save(src)
            out = root / f"out_{label}"
            out.mkdir()
            res = transforms(src, out, 1_000_000)
            files = os.listdir(out)
            assert res["status"] == "ok", res
            assert len(files) >= 14, (label, files)
            assert not any(re.search(r"_(Red|Green|Blue|Alpha)_\d", f) for f in files), files
            assert res["palette"] == (label == "palette"), res
        big = root / "big.png"
        Image.new("RGB", (100, 100)).save(big)
        assert "megapixel" in transforms(big, root, 5_000)["error"]

        for fmt, ext in (("GIF", "gif"), ("PNG", "png")):
            for n, expect in ((3, "ok"), (6, "error")):
                src = root / f"anim{n}.{ext}"
                imgs = [Image.fromarray(rng.integers(0, 256, (16, 16, 3), dtype=numpy.uint8)) for _ in range(n)]
                if fmt == "GIF":
                    imgs[0].save(src, save_all=True, append_images=imgs[1:])
                else:
                    imgs[0].save(src, save_all=True, append_images=imgs[1:], format="PNG")
                out = root / f"out_{ext}{n}"
                out.mkdir()
                res = frames(src, out, 1_000_000, 5)
                assert res["status"] == expect, (fmt, n, res)
                if expect == "ok":
                    assert len(res["images"]["Frames"]) == n, res
                else:
                    assert "5-frame limit" in res["error"], res
    print("stegoveritas driver selftest ok")


def main(argv: list[str]) -> int:
    """Dispatch on argv; the result JSON is the only thing written to stdout."""
    if argv == ["--selftest"]:
        _selftest()
        return 0
    try:
        mode, path, out = argv[0], Path(argv[1]), Path(argv[2])
        if mode == "transforms" and len(argv) == 4:
            result = transforms(path, out, int(argv[3]))
        elif mode == "frames" and len(argv) == 5:
            result = frames(path, out, int(argv[3]), int(argv[4]))
        else:
            raise IndexError
    except (IndexError, ValueError):
        print(__doc__, file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
