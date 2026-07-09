#!/usr/bin/env python3
"""Generate the steganography decision-tree mindmap for the cheatsheet.

Emits three artifacts from a single node/edge model so they never drift:

* ``decision-tree.svg``        — hand-drawn (Excalidraw-style) mindmap. Used as
                                 the thumbnail on ``/cheatsheet`` and, inlined,
                                 as the interactive map on ``/cheatsheet/map``.
* ``decision-tree.json``       — the same model as data: powers the hover
                                 tooltips (full command, detail, wiki link) on
                                 the interactive map page.
* ``decision-tree.excalidraw`` — the editable Excalidraw scene; open it at
                                 https://excalidraw.com to refine the diagram
                                 and re-export.

The SVG carries a transparent "hit" overlay per step (``class="ds-step"`` with
``data-b``/``data-s`` indices into the JSON) so the map page can attach hover,
keyboard focus and export handlers without a second renderer.

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
ROOT_DETAIL = (
    "Identify the real type with `file` (never trust the extension), then pick "
    "the branch below. On every file first: `exiftool -a -u -g1`, "
    "`strings -n 8` (add `-e l` / `-e b` for UTF-16), and `binwalk`."
)

# Each branch: label, accent color, and an ordered list of steps. A step is
# (cmd, hint, full, detail, href):
#   cmd    short mono label shown in the pill (line 1)
#   hint   dim sub-label in the pill (line 2, may be "")
#   full   the concrete command / action, copyable from the tooltip
#   detail one-sentence explanation shown on hover
#   href   a wiki path (client prepends the language prefix) or absolute URL;
#          "" for none.
Step = tuple[str, str, str, str, str]
Branch = tuple[str, str, list[Step]]

BRANCHES: list[Branch] = [
    (
        "PNG / BMP",
        "#9fef00",
        [
            (
                "zsteg -a",
                "LSB text / files",
                "zsteg -a file.png",
                "Scan every common LSB channel/bit-order combo for hidden text "
                "or files; extract a line with zsteg -E.",
                "/wiki/tools/zsteg",
            ),
            (
                "pngcheck -vtp7f",
                "CRC / IHDR size",
                "pngcheck -vtp7f file.png",
                "A CRC error in IHDR means an edited header; a shrunken "
                "width/height hides pixels below the visible image.",
                "/wiki/tools/pngcheck",
            ),
            (
                "bit planes",
                "all channels + MSB",
                "decomposer / Stegsolve",
                "Browse every bit plane and every channel including alpha; try "
                "MSB and column-major order, not just RGB LSB.",
                "/wiki/tools/decomposer",
            ),
            (
                "data after IEND",
                "carve the trailer",
                "binwalk -e file.png",
                "Data appended after the IEND chunk — carve it with "
                "binwalk/foremost or by byte offset.",
                "/wiki/tools/foremost",
            ),
            (
                "palette remap",
                "indexed PNG",
                "color remapping / randomize palette",
                "Indexed PNGs can hide an image in the palette; randomize or "
                "remap it to reveal the drawing.",
                "/wiki/tools/color_remapping",
            ),
            (
                "OpenStego",
                "randomized LSB",
                "openstego extract -sf file.png",
                "Randomized-LSB payloads that zsteg misses; needs OpenStego (and maybe a key).",
                "/wiki/tools/openstego",
            ),
        ],
    ),
    (
        "JPEG",
        "#ffa657",
        [
            (
                "steghide -p ''",
                "try empty pass",
                "steghide extract -sf file.jpg -p ''",
                "steghide is the most common JPEG tool; try the empty password "
                "first, then the filename / challenge name.",
                "/wiki/tools/steghide",
            ),
            (
                "stegseek rockyou",
                "crack passphrase",
                "stegseek file.jpg rockyou.txt",
                "Cracks a steghide passphrase against rockyou in seconds.",
                "/wiki/tools/stegseek",
            ),
            (
                "outguess / jsteg",
                "jphide",
                "outguess -r file.jpg out.txt",
                "If it isn't steghide, try OutGuess, jsteg, or JPHide (jpseek). "
                "zsteg does NOT work on JPEG.",
                "/wiki/tools/outguess",
            ),
            (
                "stegdetect",
                "statistical",
                "stegdetect file.jpg",
                "Statistical detector that hints which JPEG tool was used.",
                "/wiki/techniques/images",
            ),
        ],
    ),
    (
        "GIF / APNG",
        "#d2a8ff",
        [
            (
                "extract frames",
                "ffmpeg -vsync 0",
                "ffmpeg -i file.gif -vsync 0 out/f%d.png",
                "Animations can carry zero-duration frames; extract every frame "
                "then run the PNG checklist on them.",
                "/wiki/techniques/images",
            ),
            (
                "frame durations",
                "morse / binary",
                "identify -verbose file.gif",
                "Per-frame delays can encode morse / binary / ASCII.",
                "/wiki/tools/identify",
            ),
            (
                "diff frames",
                "consecutive",
                "compare frame N vs N+1",
                "A payload can live in the difference between two near-identical frames.",
                "/wiki/techniques/images",
            ),
            (
                "palette tricks",
                "",
                "randomize / remap palette",
                "Same indexed-color palette tricks as PNG.",
                "/wiki/tools/color_remapping",
            ),
        ],
    ),
    (
        "AUDIO",
        "#79c0ff",
        [
            (
                "spectrogram FIRST",
                "Audacity / sox",
                "sox file.wav -n spectrogram -o spec.png",
                "View the frequency domain first — text and QR codes are often "
                "drawn there; check above 20 kHz and below 20 Hz.",
                "/wiki/tools/spectrogram",
            ),
            (
                "waveform",
                "→ Morse",
                "audacity file.wav",
                "Obvious on/off bursts in the waveform decode as Morse.",
                "/wiki/techniques/audio",
            ),
            (
                "WAV LSB",
                "stegolsb wavsteg",
                "stegolsb wavsteg -r -i file.wav -o out.txt -n 1 -b 1000",
                "LSB payloads in WAV samples; they often don't start at sample 0.",
                "/wiki/techniques/audio",
            ),
            (
                "SSTV / DTMF / FSK",
                "QSSTV / minimodem",
                "minimodem --rx 1200",
                "Decode images with QSSTV, phone tones with a DTMF decoder, "
                "modem tones with minimodem / multimon-ng.",
                "/wiki/techniques/audio",
            ),
            (
                "steghide",
                "DeepSound",
                "steghide extract -sf file.wav",
                "Passworded containers: steghide (WAV/AU) or DeepSound.",
                "/wiki/tools/steghide",
            ),
        ],
    ),
    (
        "VIDEO",
        "#f778ba",
        [
            (
                "ffprobe streams",
                "count tracks",
                "ffprobe file.mp4",
                "An extra subtitle, attachment or data track is often the whole trick.",
                "/wiki/techniques/video",
            ),
            (
                "extract frames",
                "ffmpeg -vsync 0",
                "ffmpeg -i file.mp4 -vsync 0 out/f%05d.png",
                "Run the PNG checklist (zsteg, bit planes) on the lossless frames.",
                "/wiki/techniques/video",
            ),
            (
                "subtitle / attach",
                "-map 0:s / dump",
                "ffmpeg -i file.mkv -map 0:s:0 subs.srt",
                "Extract subtitle tracks and attached files (fonts, images).",
                "/wiki/techniques/video",
            ),
            (
                "audio track",
                "→ spectrogram",
                "ffmpeg -i file.mp4 -vn audio.wav",
                "Pull the audio track, then treat it as an audio challenge (spectrogram first).",
                "/wiki/techniques/audio",
            ),
            (
                "moov / trailing",
                "exiftool · binwalk",
                "binwalk file.mp4",
                "Metadata and bytes past the moov atom.",
                "/wiki/tools/exiftool",
            ),
        ],
    ),
    (
        "TEXT",
        "#56d4bc",
        [
            (
                "cat -A → stegsnow",
                "whitespace",
                "stegsnow -C file.txt",
                "Trailing spaces/tabs; reveal with cat -A, extract with stegsnow.",
                "/wiki/tools/stegsnow",
            ),
            (
                "zero-width",
                "U+200B / C / D",
                "compare wc -c to the visible length",
                "Invisible zero-width characters; inspect code points with xxd "
                "or a zero-width decoder.",
                "/wiki/techniques/text",
            ),
            (
                "homoglyphs",
                "mixed alphabets",
                "Irongeek homoglyph decoder",
                "Latin a vs Cyrillic а — a homoglyph decoder separates them.",  # noqa: RUF001
                "/wiki/techniques/text",
            ),
            (
                "encodings",
                "CyberChef Magic",
                "CyberChef → Magic",
                "Brainfuck / Whitespace / Piet / Malbolge and base-N chains; try CyberChef Magic.",
                "/wiki/techniques/encodings",
            ),
        ],
    ),
    (
        "ARCHIVE / DOC",
        "#ff7b72",
        [
            (
                "unzip / 7z",
                "appended zip",
                "unzip file.png",
                "An appended archive; unzip / 7z l often just works.",
                "/wiki/tools/binwalk",
            ),
            (
                "binwalk -e",
                "carve embedded",
                "binwalk -e file.bin",
                "Carve embedded / compressed files out of the container.",
                "/wiki/tools/binwalk",
            ),
            (
                "polyglot?",
                "two magic bytes",
                "check for multiple magic numbers",
                "A file valid as two formats (PDF/ZIP, JPEG/ZIP, GIF/JS); file will not flag it.",
                "/wiki/techniques/files-archives",
            ),
            (
                "pdf / docx / apk",
                "it's a zip",
                "7z x file.docx",
                ".docx / .pptx / .jar / .apk are ZIPs; PDFs: pdfdetach -saveall.",
                "/wiki/tools/pdfinfo",
            ),
            (
                "fcrackzip -u -D",
                "crack zip",
                "fcrackzip -u -D -p rockyou.txt file.zip",
                "ZipCrypto is weak (also bkcrack known-plaintext); AES-256 is not.",
                "/wiki/cheatsheet/brute-force",
            ),
        ],
    ),
    (
        "PCAP / NET",
        "#e3b341",
        [
            (
                "tshark -qz io,phs",
                "what's inside",
                "tshark -r file.pcap -qz io,phs",
                "The protocol hierarchy shows which protocols carry data.",
                "/wiki/cheatsheet/network",
            ),
            (
                "--export-objects",
                "carve HTTP/SMB",
                "tshark -r file.pcap --export-objects http,out/",
                "Carve transferred files out of HTTP / SMB / TFTP.",
                "/wiki/cheatsheet/network",
            ),
            (
                "usb.capdata",
                "keystrokes",
                "tshark -r f.pcap -Y usb.capdata -T fields -e usb.capdata",
                "USB HID captures decode to keystrokes / mouse movement.",
                "/wiki/cheatsheet/network",
            ),
            (
                "dns.qry.name",
                "exfil in subdomains",
                "tshark -r f.pcap -Y dns -T fields -e dns.qry.name",
                "Data exfiltrated in DNS subdomains.",
                "/wiki/cheatsheet/network",
            ),
        ],
    ),
    (
        "UNKNOWN / RAW",
        "#8b949e",
        [
            (
                "file / hex editor",
                "identify",
                "file target",
                "Trust file over the extension; inspect the bytes in a hex editor.",
                "/wiki/tools/file",
            ),
            (
                "binvis.io",
                "visualize bytes",
                "open binvis.io",
                "Visualize byte entropy / patterns to spot hidden structure.",
                "https://binvis.io/",
            ),
            (
                "raw import",
                "GIMP / Audacity",
                "import as raw data",
                "Import an unknown blob as raw image (GIMP) or raw audio (Audacity).",
                "/wiki/techniques/steganalysis",
            ),
            (
                "QR / Braille",
                "decode blob",
                "zbarimg --raw img.png",
                "Decode QR / barcodes with zbarimg; Braille / semaphore by hand.",
                "/wiki/techniques/encodings",
            ),
        ],
    ),
]

# --- Geometry ------------------------------------------------------------

# Fixed column width so pills never overlap; the canvas grows with the number
# of branches instead of squeezing them.
MARGIN_X = 20
COL_W = 172
W = MARGIN_X * 2 + COL_W * len(BRANCHES)
PILL_W = 154
ROOT_W, ROOT_H = 480, 66
ROOT_X, ROOT_Y = (W - ROOT_W) / 2, 20
HEADER_Y, HEADER_H = 150, 40
STEP_Y0, STEP_H, STEP_PITCH = 214, 50, 62
MAX_STEPS = max(len(steps) for _, _, steps in BRANCHES)
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
        f'width="{W}" height="{H}" role="img" class="decision-tree-svg" '
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
        f'font-size="12" fill="{DIM_TEXT}">numbers = try in this order · hover for detail</text>'
    )

    shapes: list[str] = []
    labels: list[str] = []
    # Transparent interaction overlays, drawn last so they sit on top and
    # receive pointer/keyboard events on the map page (invisible otherwise).
    hits: list[str] = []

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
    root_aria = f"{ROOT_TITLE}: run first — {ROOT_SUB}"
    hits.append(
        f'<rect class="ds-step" data-root="1" x="{ROOT_X:.0f}" y="{ROOT_Y}" '
        f'width="{ROOT_W}" height="{ROOT_H}" rx="14" fill="#9fef00" stroke="#9fef00" '
        f'fill-opacity="0" stroke-opacity="0" pointer-events="all" tabindex="0" '
        f'role="button" aria-label="{html.escape(root_aria)}"/>'
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
        for j, (l1, l2, _full, _detail, _href) in enumerate(steps):
            sy = STEP_Y0 + j * STEP_PITCH
            shapes.append(
                f'<rect x="{hx:.0f}" y="{sy}" width="{PILL_W}" height="{STEP_H}" '
                f'rx="11" fill="{PILL_FILL}" stroke="{color}" stroke-width="1.4" opacity="0.98"/>'
            )
            # Order badge.
            bx, byc = hx + 15, sy + STEP_H / 2
            shapes.append(f'<circle cx="{bx:.0f}" cy="{byc:.0f}" r="10" fill="{color}"/>')
            labels.append(
                f'<text x="{bx:.0f}" y="{byc + 4:.0f}" text-anchor="middle" '
                f'font-size="12" font-weight="700" fill="{DARK_TEXT}">{j + 1}</text>'
            )
            tx = hx + 32
            if l2:
                labels.append(
                    f'<text x="{tx:.0f}" y="{sy + 21}" font-family="{MONO}" '
                    f'font-size="11.5" fill="{LIGHT_TEXT}" font-weight="600">'
                    f"{html.escape(l1)}</text>"
                )
                labels.append(
                    f'<text x="{tx:.0f}" y="{sy + 37}" font-size="11" '
                    f'fill="{DIM_TEXT}">{html.escape(l2)}</text>'
                )
            else:
                labels.append(
                    f'<text x="{tx:.0f}" y="{sy + 30}" font-family="{MONO}" '
                    f'font-size="11.5" fill="{LIGHT_TEXT}" font-weight="600">'
                    f"{html.escape(l1)}</text>"
                )
            aria = f"{label} step {j + 1}: {l1}" + (f" — {l2}" if l2 else "")
            hits.append(
                f'<rect class="ds-step" data-b="{i}" data-s="{j}" x="{hx:.0f}" y="{sy}" '
                f'width="{PILL_W}" height="{STEP_H}" rx="11" fill="{color}" stroke="{color}" '
                f'fill-opacity="0" stroke-opacity="0" pointer-events="all" tabindex="0" '
                f'role="button" aria-label="{html.escape(aria)}"/>'
            )

    parts.append(f'<g filter="url(#rough)">{"".join(shapes)}</g>')
    parts.append("".join(labels))
    parts.append(f'<g class="ds-hits">{"".join(hits)}</g>')
    parts.append("</svg>")
    return "".join(parts)


# --- Data (JSON) renderer ------------------------------------------------


def data() -> dict:
    """The diagram model as data, consumed by the interactive map page."""
    return {
        "root": {"title": ROOT_TITLE, "sub": ROOT_SUB, "detail": ROOT_DETAIL},
        "branches": [
            {
                "label": label,
                "color": color,
                "steps": [
                    {
                        "n": j + 1,
                        "cmd": l1,
                        "hint": l2,
                        "full": full,
                        "detail": detail,
                        "href": href,
                    }
                    for j, (l1, l2, full, detail, href) in enumerate(steps)
                ],
            }
            for label, color, steps in BRANCHES
        ],
    }


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
    for extra in (
        "points",
        "text",
        "fontSize",
        "fontFamily",
        "textAlign",
        "verticalAlign",
        "containerId",
        "originalText",
        "lineHeight",
        "autoResize",
        "startBinding",
        "endBinding",
        "startArrowhead",
        "endArrowhead",
    ):
        if extra in kw:
            base[extra] = kw[extra]
    return base


def _box(idx, eid, x, y, w, h, stroke, bg, text, fontsize=16, textcolor=None):
    """A rectangle plus its bound text label -> two elements."""
    tid = f"{eid}-t"
    rect = _el(
        idx,
        id=eid,
        type="rectangle",
        x=x,
        y=y,
        width=w,
        height=h,
        strokeColor=stroke,
        backgroundColor=bg,
        boundElements=[{"type": "text", "id": tid}],
    )
    txt = _el(
        idx + 1,
        id=tid,
        type="text",
        x=x + 6,
        y=y + h / 2 - fontsize / 2,
        width=w - 12,
        height=fontsize + 4,
        strokeColor=textcolor or "#1e1e1e",
        roundness=None,
        text=text,
        originalText=text,
        fontSize=fontsize,
        fontFamily=1,
        textAlign="center",
        verticalAlign="middle",
        containerId=eid,
        lineHeight=1.25,
        autoResize=True,
        boundElements=None,
    )
    return [rect, txt]


def excalidraw() -> dict:
    els: list[dict] = []
    idx = 0
    # Root.
    els += _box(
        idx,
        "root",
        ROOT_X,
        ROOT_Y,
        ROOT_W,
        ROOT_H,
        "#2f9e00",
        "#f7ffe6",
        f"{ROOT_TITLE}\n{ROOT_SUB}",
        fontsize=16,
    )
    idx += 2
    for i, (label, color, steps) in enumerate(BRANCHES):
        cx = col_center(i)
        hx = cx - PILL_W / 2
        hid = f"h{i}"
        els += _box(
            idx,
            hid,
            hx,
            HEADER_Y,
            PILL_W,
            HEADER_H,
            color,
            color,
            label,
            fontsize=15,
            textcolor="#0b121f",
        )
        idx += 2
        # Root -> header arrow.
        els.append(
            _el(
                idx,
                id=f"e-root-{i}",
                type="arrow",
                x=W / 2,
                y=ROOT_Y + ROOT_H,
                width=cx - W / 2,
                height=HEADER_Y - (ROOT_Y + ROOT_H),
                strokeColor="#8a97ab",
                roundness={"type": 2},
                points=[[0, 0], [cx - W / 2, HEADER_Y - (ROOT_Y + ROOT_H)]],
                startBinding=None,
                endBinding=None,
                startArrowhead=None,
                endArrowhead=None,
                boundElements=None,
            )
        )
        idx += 1
        for j, (l1, l2, _full, _detail, _href) in enumerate(steps):
            sy = STEP_Y0 + j * STEP_PITCH
            sid = f"s{i}-{j}"
            text = f"{j + 1}. {l1}" + (f"\n{l2}" if l2 else "")
            els += _box(
                idx,
                sid,
                hx,
                sy,
                PILL_W,
                STEP_H,
                color,
                "#16233a",
                text,
                fontsize=12,
                textcolor="#d4dbe6",
            )
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
    (OUT_DIR / "decision-tree.json").write_text(
        json.dumps(data(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "decision-tree.excalidraw").write_text(
        json.dumps(excalidraw(), indent=2), encoding="utf-8"
    )
    print(
        f"wrote decision-tree.svg ({W}x{H}), decision-tree.json and "
        f"decision-tree.excalidraw to {OUT_DIR}"
    )


if __name__ == "__main__":
    main()
