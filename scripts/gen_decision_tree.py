#!/usr/bin/env python3
"""Generate the steganography decision-tree mindmap for the wiki cheatsheet.

Emits two artifacts from a single node/edge model so they never drift:

* ``decision-tree.svg``       — hand-drawn (Excalidraw-style) mindmap embedded
                                in ``/wiki/cheatsheet``.
* ``decision-tree.excalidraw`` — the editable Excalidraw scene; open it at
                                 https://excalidraw.com to refine the diagram
                                 and re-export.

Run: ``python scripts/gen_decision_tree.py`` (pure standard library).
"""

from __future__ import annotations

import html
import json
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "aperisolve" / "static" / "img" / "cheatsheet"

# --- Diagram model -------------------------------------------------------

ROOT_TITLE = "ANY FILE"
ROOT_SUB = "run first:  file · exiftool · strings · binwalk"

# (label, accent color, [ (line1, line2), ... ] ordered steps)
BRANCHES: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("PNG / BMP", "#9fef00", [
        ("zsteg -a", "LSB text / files"),
        ("pngcheck -vtp7f", "CRC / IHDR size"),
        ("bit planes", "all channels + MSB"),
        ("data after IEND", "carve the trailer"),
        ("palette remap", "indexed PNG"),
        ("OpenStego", "randomized LSB"),
    ]),
    ("JPEG", "#ffa657", [
        ("steghide -p ''", "try empty pass"),
        ("stegseek rockyou", "crack passphrase"),
        ("outguess / jsteg", "jphide"),
        ("stegdetect", "statistical"),
    ]),
    ("GIF / APNG", "#d2a8ff", [
        ("extract frames", "ffmpeg -vsync 0"),
        ("frame durations", "morse / binary"),
        ("diff frames", "consecutive"),
        ("palette tricks", ""),
    ]),
    ("AUDIO", "#79c0ff", [
        ("spectrogram FIRST", "Audacity / sox"),
        ("waveform", "-> Morse"),
        ("WAV LSB", "stegolsb wavsteg"),
        ("SSTV / DTMF / FSK", "QSSTV / minimodem"),
        ("steghide", "DeepSound"),
    ]),
    ("VIDEO", "#f778ba", [
        ("ffprobe streams", "count tracks"),
        ("extract frames", "ffmpeg -vsync 0"),
        ("subtitle / attach", "-map 0:s / dump"),
        ("audio track", "-> spectrogram"),
        ("moov / trailing", "exiftool · binwalk"),
    ]),
    ("TEXT", "#56d4bc", [
        ("cat -A -> stegsnow", "whitespace"),
        ("zero-width", "U+200B / C / D"),
        ("homoglyphs", "mixed alphabets"),
        ("encodings", "CyberChef Magic"),
    ]),
    ("ARCHIVE / DOC", "#ff7b72", [
        ("unzip / 7z", "appended zip"),
        ("binwalk -e", "carve embedded"),
        ("polyglot?", "two magic bytes"),
        ("pdf / docx / apk", "it's a zip"),
        ("fcrackzip -u -D", "crack zip"),
    ]),
    ("UNKNOWN / RAW", "#8b949e", [
        ("file / hexed.it", "identify"),
        ("binvis.io", "visualize bytes"),
        ("raw import", "GIMP / Audacity"),
        ("QR / Braille", "decode blob"),
    ]),
]

# --- Geometry ------------------------------------------------------------

W = 1400
MARGIN_X = 20
COL_W = (W - 2 * MARGIN_X) / len(BRANCHES)
PILL_W = 154
ROOT_W, ROOT_H = 480, 66
ROOT_X, ROOT_Y = (W - ROOT_W) / 2, 20
HEADER_Y, HEADER_H = 150, 40
STEP_Y0, STEP_H, STEP_PITCH = 214, 50, 62
MAX_STEPS = max(len(b[2]) for b in BRANCHES)
H = int(STEP_Y0 + MAX_STEPS * STEP_PITCH + 18)

DARK_TEXT = "#0b121f"
LIGHT_TEXT = "#d4dbe6"
DIM_TEXT = "#8a97ab"
PANEL = "#0d1522"
PILL_FILL = "#16233a"


def col_center(i: int) -> float:
    return MARGIN_X + COL_W * (i + 0.5)


# --- SVG renderer --------------------------------------------------------

FONT = "'Segoe Print','Bradley Hand','Comic Sans MS',ui-rounded,sans-serif"
MONO = "'Fira Code',ui-monospace,monospace"


def svg() -> str:
    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="Steganography decision tree by file type" '
        f'font-family="{FONT}">'
    )
    parts.append(
        '<defs><filter id="rough" filterUnits="userSpaceOnUse" '
        f'x="0" y="0" width="{W}" height="{H}">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.013" '
        'numOctaves="2" seed="7" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="2.4" '
        'xChannelSelector="R" yChannelSelector="G"/></filter></defs>'
    )
    # Backdrop panel + title.
    parts.append(
        f'<rect x="4" y="4" width="{W - 8}" height="{H - 8}" rx="16" '
        f'fill="{PANEL}" stroke="#9fef0022" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="24" y="34" font-family="{MONO}" font-size="17" '
        f'fill="#9fef00" font-weight="700">Steganography — where to look first</text>'
    )
    parts.append(
        f'<text x="{W - 24}" y="34" text-anchor="end" font-family="{MONO}" '
        f'font-size="12" fill="{DIM_TEXT}">numbers = try in this order · details below</text>'
    )

    shapes: list[str] = []
    labels: list[str] = []

    # Connectors root -> headers (drawn first, behind).
    rbx, rby = W / 2, ROOT_Y + ROOT_H
    for i in range(len(BRANCHES)):
        cx = col_center(i)
        htop = HEADER_Y
        shapes.append(
            f'<path d="M {rbx:.0f} {rby:.0f} C {rbx:.0f} {rby + 34:.0f}, '
            f'{cx:.0f} {htop - 28:.0f}, {cx:.0f} {htop:.0f}" '
            f'fill="none" stroke="#8a97ab" stroke-width="1.6" opacity="0.6"/>'
        )

    # Root node.
    shapes.append(
        f'<rect x="{ROOT_X:.0f}" y="{ROOT_Y}" width="{ROOT_W}" height="{ROOT_H}" '
        f'rx="14" fill="#101a2b" stroke="#9fef00" stroke-width="2.4"/>'
    )
    labels.append(
        f'<text x="{W / 2:.0f}" y="{ROOT_Y + 28}" text-anchor="middle" '
        f'font-family="{MONO}" font-size="20" font-weight="700" fill="#9fef00">{ROOT_TITLE}</text>'
    )
    labels.append(
        f'<text x="{W / 2:.0f}" y="{ROOT_Y + 50}" text-anchor="middle" '
        f'font-family="{MONO}" font-size="12.5" fill="{LIGHT_TEXT}">{html.escape(ROOT_SUB)}</text>'
    )

    for i, (label, color, steps) in enumerate(BRANCHES):
        cx = col_center(i)
        hx = cx - PILL_W / 2
        # Column spine behind the pills.
        last_cy = STEP_Y0 + (len(steps) - 1) * STEP_PITCH + STEP_H / 2
        shapes.append(
            f'<path d="M {cx:.0f} {HEADER_Y + HEADER_H} L {cx:.0f} {last_cy:.0f}" '
            f'stroke="{color}" stroke-width="1.6" opacity="0.5" fill="none"/>'
        )
        # Category header (filled accent).
        shapes.append(
            f'<rect x="{hx:.0f}" y="{HEADER_Y}" width="{PILL_W}" height="{HEADER_H}" '
            f'rx="12" fill="{color}" stroke="{color}" stroke-width="1.5"/>'
        )
        labels.append(
            f'<text x="{cx:.0f}" y="{HEADER_Y + 25}" text-anchor="middle" '
            f'font-size="15" font-weight="700" fill="{DARK_TEXT}">{html.escape(label)}</text>'
        )
        # Steps.
        for j, (l1, l2) in enumerate(steps):
            sy = STEP_Y0 + j * STEP_PITCH
            shapes.append(
                f'<rect x="{hx:.0f}" y="{sy}" width="{PILL_W}" height="{STEP_H}" '
                f'rx="11" fill="{PILL_FILL}" stroke="{color}" stroke-width="1.4" opacity="0.98"/>'
            )
            # Order badge.
            bx, byc = hx + 15, sy + STEP_H / 2
            shapes.append(
                f'<circle cx="{bx:.0f}" cy="{byc:.0f}" r="10" fill="{color}"/>'
            )
            labels.append(
                f'<text x="{bx:.0f}" y="{byc + 4:.0f}" text-anchor="middle" '
                f'font-size="12" font-weight="700" fill="{DARK_TEXT}">{j + 1}</text>'
            )
            tx = hx + 32
            if l2:
                labels.append(
                    f'<text x="{tx:.0f}" y="{sy + 21}" font-family="{MONO}" '
                    f'font-size="11.5" fill="{LIGHT_TEXT}" font-weight="600">'
                    f'{html.escape(l1)}</text>'
                )
                labels.append(
                    f'<text x="{tx:.0f}" y="{sy + 37}" font-size="11" '
                    f'fill="{DIM_TEXT}">{html.escape(l2)}</text>'
                )
            else:
                labels.append(
                    f'<text x="{tx:.0f}" y="{sy + 30}" font-family="{MONO}" '
                    f'font-size="11.5" fill="{LIGHT_TEXT}" font-weight="600">'
                    f'{html.escape(l1)}</text>'
                )

    parts.append(f'<g filter="url(#rough)">{"".join(shapes)}</g>')
    parts.append("".join(labels))
    parts.append("</svg>")
    return "".join(parts)


# --- Excalidraw scene renderer ------------------------------------------


def _el(idx: int, **kw) -> dict:
    base = {
        "id": kw["id"],
        "type": kw["type"],
        "x": kw["x"],
        "y": kw["y"],
        "width": kw.get("width", 0),
        "height": kw.get("height", 0),
        "angle": 0,
        "strokeColor": kw.get("strokeColor", "#1e1e1e"),
        "backgroundColor": kw.get("backgroundColor", "transparent"),
        "fillStyle": "solid",
        "strokeWidth": kw.get("strokeWidth", 2),
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "index": f"a{idx}",
        "roundness": kw.get("roundness", {"type": 3}),
        "seed": 1000 + idx * 7,
        "version": 1,
        "versionNonce": 100000 + idx * 13,
        "isDeleted": False,
        "boundElements": kw.get("boundElements"),
        "updated": 1,
        "link": None,
        "locked": False,
    }
    for extra in ("points", "text", "fontSize", "fontFamily", "textAlign",
                  "verticalAlign", "containerId", "originalText", "lineHeight",
                  "autoResize", "startBinding", "endBinding", "startArrowhead",
                  "endArrowhead"):
        if extra in kw:
            base[extra] = kw[extra]
    return base


def _box(idx, eid, x, y, w, h, stroke, bg, text, fontsize=16, textcolor=None):
    """A rectangle plus its bound text label -> two elements."""
    tid = f"{eid}-t"
    rect = _el(
        idx, id=eid, type="rectangle", x=x, y=y, width=w, height=h,
        strokeColor=stroke, backgroundColor=bg, boundElements=[{"type": "text", "id": tid}],
    )
    txt = _el(
        idx + 1, id=tid, type="text", x=x + 6, y=y + h / 2 - fontsize / 2,
        width=w - 12, height=fontsize + 4, strokeColor=textcolor or "#1e1e1e",
        roundness=None, text=text, originalText=text, fontSize=fontsize,
        fontFamily=1, textAlign="center", verticalAlign="middle",
        containerId=eid, lineHeight=1.25, autoResize=True, boundElements=None,
    )
    return [rect, txt]


def excalidraw() -> dict:
    els: list[dict] = []
    idx = 0
    # Root.
    els += _box(idx, "root", ROOT_X, ROOT_Y, ROOT_W, ROOT_H, "#2f9e00", "#f7ffe6",
                f"{ROOT_TITLE}\n{ROOT_SUB}", fontsize=16)
    idx += 2
    for i, (label, color, steps) in enumerate(BRANCHES):
        cx = col_center(i)
        hx = cx - PILL_W / 2
        hid = f"h{i}"
        els += _box(idx, hid, hx, HEADER_Y, PILL_W, HEADER_H, color, color,
                    label, fontsize=15, textcolor="#0b121f")
        idx += 2
        # Root -> header arrow.
        els.append(_el(
            idx, id=f"e-root-{i}", type="arrow", x=W / 2, y=ROOT_Y + ROOT_H,
            width=cx - W / 2, height=HEADER_Y - (ROOT_Y + ROOT_H),
            strokeColor="#8a97ab", roundness={"type": 2},
            points=[[0, 0], [cx - W / 2, HEADER_Y - (ROOT_Y + ROOT_H)]],
            startBinding=None, endBinding=None,
            startArrowhead=None, endArrowhead=None, boundElements=None,
        ))
        idx += 1
        for j, (l1, l2) in enumerate(steps):
            sy = STEP_Y0 + j * STEP_PITCH
            sid = f"s{i}-{j}"
            text = f"{j + 1}. {l1}" + (f"\n{l2}" if l2 else "")
            els += _box(idx, sid, hx, sy, PILL_W, STEP_H, color, "#16233a",
                        text, fontsize=12, textcolor="#d4dbe6")
            idx += 2
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/Zeecka/AperiSolve",
        "elements": els,
        "appState": {"gridSize": None, "viewBackgroundColor": "#0d1522"},
        "files": {},
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "decision-tree.svg").write_text(svg(), encoding="utf-8")
    (OUT_DIR / "decision-tree.excalidraw").write_text(
        json.dumps(excalidraw(), indent=2), encoding="utf-8"
    )
    print(f"wrote decision-tree.svg ({W}x{H}) and decision-tree.excalidraw to {OUT_DIR}")


if __name__ == "__main__":
    main()
