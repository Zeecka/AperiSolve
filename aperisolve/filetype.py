"""File-type classification shared by the worker and the analyzer registry.

``detect_file_type`` derives a :class:`FileType` from a stored upload so the
worker can gate analyzers by content type and (later) the web layer can pick a
type-appropriate preview. Detection is best-effort and **never raises**: every
backend is wrapped and an undetectable file degrades to
``application/octet-stream`` / ``kind="other"`` / empty ``tags``.

Detection order (first confident hit wins):

1. ``file --mime-type -b <path>`` (libmagic CLI, fixed argv, 5 s timeout).
2. Pillow ``Image.open(...).format`` -> ``image/<format>``.
3. An extension table (audio/video/pdf formats + :data:`aperisolve.config.IMAGE_EXTENSIONS`).
4. ``application/octet-stream``.
"""

import functools
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from aperisolve.config import IMAGE_EXTENSIONS

# Wall clock for the libmagic CLI probe; short because the worker inlines it.
_FILE_CMD_TIMEOUT = 5

# Bound on distinct paths remembered by the cached entrypoint.
_CACHE_SIZE = 1024


@dataclass(frozen=True, slots=True)
class FileType:
    """Detected content type of an upload.

    ``kind`` (one of ``"image"``, ``"audio"``, ``"video"``, ``"pdf"``,
    ``"other"``) drives the frontend preview; ``tags`` gate which analyzers run
    (see ``aperisolve.analyzers.base_analyzer.SubprocessAnalyzer.accepts``).
    """

    mime: str
    kind: str
    tags: frozenset[str]


# Format tags of interest, grouped by kind. A tag both marks the concrete
# format (``png``/``wav``/...) and, via these sets, back-derives the kind when
# ``file(1)`` labels a container ambiguously (e.g. ``application/ogg``).
_IMAGE_FORMATS = frozenset({"png", "jpeg", "gif", "bmp", "webp", "tiff"})
_AUDIO_FORMATS = frozenset({"wav", "mp3", "flac", "ogg", "m4a", "au"})
_VIDEO_FORMATS = frozenset(
    {"mp4", "webm", "avi", "flv", "mkv", "mov", "wmv", "mpeg", "m4v", "ogv", "3gp", "ts"},
)

# Known MIME strings (as emitted by libmagic/Pillow/the extension table),
# mapped to their canonical format tag.
_MIME_FORMAT_TAGS: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/gif": "gif",
    "image/bmp": "bmp",
    "image/x-bmp": "bmp",
    "image/x-ms-bmp": "bmp",
    "image/webp": "webp",
    "image/tiff": "tiff",
    "image/x-tiff": "tiff",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/vnd.wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/x-mp3": "mp3",
    "audio/flac": "flac",
    "audio/x-flac": "flac",
    "audio/ogg": "ogg",
    "application/ogg": "ogg",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/basic": "au",
    "audio/x-au": "au",
    "video/mp4": "mp4",
    "video/webm": "webm",
    "video/x-msvideo": "avi",
    "video/avi": "avi",
    "video/x-flv": "flv",
    "video/x-matroska": "mkv",
    "video/quicktime": "mov",
    "video/x-ms-wmv": "wmv",
    "video/mpeg": "mpeg",
    "video/x-m4v": "m4v",
    "video/ogg": "ogv",
    "video/3gpp": "3gp",
    "video/mp2t": "ts",
    "application/pdf": "pdf",
}

# Kind -> the tag added alongside the format tag. ``other`` contributes none.
_KIND_TAG: dict[str, str] = {
    "image": "image",
    "audio": "audio",
    "video": "video",
    "pdf": "pdf",
}

# MIME strings that carry no format information; treated as "not confident" so
# detection falls through to Pillow / the extension table.
_UNINFORMATIVE_MIMES = frozenset(
    {"application/octet-stream", "inode/x-empty", "application/x-empty"},
)

# Extension -> MIME fallback for audio/document types (step 3). Image
# extensions are merged in from IMAGE_EXTENSIONS by _build_ext_mime_table.
_DOC_AUDIO_EXT_MIME: dict[str, str] = {
    ".wav": "audio/x-wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".au": "audio/basic",
    ".pdf": "application/pdf",
}

# Extension -> MIME fallback for video types (step 3). Kept separate from the
# audio/document table only for readability; both are merged in below.
_VIDEO_EXT_MIME: dict[str, str] = {
    ".mp4": "video/mp4",
    ".m4v": "video/x-m4v",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".flv": "video/x-flv",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".wmv": "video/x-ms-wmv",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
    ".ogv": "video/ogg",
    ".3gp": "video/3gpp",
    ".ts": "video/mp2t",
}

# Image extensions whose MIME is not simply ``image/<ext>``.
_IMAGE_EXT_MIME_OVERRIDES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


def _image_ext_to_mime(ext: str) -> str:
    """Map a (lowercased) image extension to its MIME type."""
    return _IMAGE_EXT_MIME_OVERRIDES.get(ext, f"image/{ext.removeprefix('.')}")


def _build_ext_mime_table() -> dict[str, str]:
    """Extension -> MIME fallback table (audio/video/pdf + configured image types)."""
    table = dict(_DOC_AUDIO_EXT_MIME)
    table.update(_VIDEO_EXT_MIME)
    for ext in IMAGE_EXTENSIONS:
        table.setdefault(ext.lower(), _image_ext_to_mime(ext.lower()))
    return table


_EXT_TO_MIME: dict[str, str] = _build_ext_mime_table()


def _kind_for(mime: str, fmt: str) -> str:
    """Derive the coarse ``kind`` from the MIME prefix, backed by the format tag."""
    if mime.startswith("image/") or fmt in _IMAGE_FORMATS:
        return "image"
    if mime.startswith("video/") or fmt in _VIDEO_FORMATS:
        return "video"
    if mime.startswith("audio/") or fmt in _AUDIO_FORMATS:
        return "audio"
    if mime == "application/pdf" or fmt == "pdf":
        return "pdf"
    return "other"


def _tags_for(kind: str, fmt: str) -> frozenset[str]:
    """Build the analyzer-gating tag set (format tag union kind tag)."""
    tags: set[str] = set()
    if fmt:
        tags.add(fmt)
    kind_tag = _KIND_TAG.get(kind)
    if kind_tag:
        tags.add(kind_tag)
    return frozenset(tags)


def _classify(mime: str) -> FileType:
    """Turn a (possibly empty) MIME string into a :class:`FileType`."""
    fmt = _MIME_FORMAT_TAGS.get(mime, "")
    kind = _kind_for(mime, fmt)
    tags = _tags_for(kind, fmt)
    return FileType(mime=mime or "application/octet-stream", kind=kind, tags=tags)


def _mime_from_file_cmd(path: Path) -> str:
    """Probe libmagic via the ``file`` CLI; empty string on any failure."""
    try:
        result = subprocess.run(  # noqa: S603
            ["file", "--mime-type", "-b", str(path)],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=_FILE_CMD_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    # A non-zero exit means libmagic could not read the file; its stdout then
    # holds an error message, not a MIME type, so ignore it.
    if result.returncode != 0:
        return ""
    mime = result.stdout.split(";")[0].strip().lower()
    # ``file`` reports a missing/unreadable path as a prose "cannot open ..."
    # line while still exiting 0; a real MIME is a single ``type/subtype`` token.
    if "/" not in mime or " " in mime:
        return ""
    return mime


def _mime_from_pillow(path: Path) -> str:
    """Ask Pillow for the image format; empty string when it cannot decode."""
    try:
        with Image.open(path) as img:
            fmt = img.format
    except (OSError, UnidentifiedImageError, ValueError):
        return ""
    return f"image/{fmt.lower()}" if fmt else ""


def _mime_from_extension(path: Path) -> str:
    """Look the file extension up in the fallback table; empty if unknown."""
    return _EXT_TO_MIME.get(path.suffix.lower(), "")


def _is_confident(mime: str) -> bool:
    """Return whether a non-empty, non-generic MIME should win over later fallbacks."""
    return bool(mime) and mime not in _UNINFORMATIVE_MIMES


def _detect_mime(path: Path) -> str:
    """Run the detection chain and return the first confident MIME string."""
    file_mime = _mime_from_file_cmd(path)
    if _is_confident(file_mime):
        return file_mime
    pillow_mime = _mime_from_pillow(path)
    if pillow_mime:
        return pillow_mime
    ext_mime = _mime_from_extension(path)
    if ext_mime:
        return ext_mime
    return file_mime or "application/octet-stream"


def detect_file_type_uncached(path: Path) -> FileType:
    """Classify ``path`` from its content; best-effort and never raises.

    The individual backends already swallow their own errors; the outer guard is
    defense in depth because ``workers.analyze_image`` inlines this call and a
    stray exception would abort the whole submission.
    """
    try:
        mime = _detect_mime(path)
    except Exception:  # noqa: BLE001
        mime = "application/octet-stream"
    return _classify(mime)


@functools.lru_cache(maxsize=_CACHE_SIZE)
def _detect_cached(path_str: str, mtime_ns: int, size: int) -> FileType:
    """Return the cached classification keyed on (path, mtime, size)."""
    _ = (mtime_ns, size)
    return detect_file_type_uncached(Path(path_str))


def detect_file_type(path: Path) -> FileType:
    """Classify ``path``, memoized on (path, mtime, size); never raises.

    A file changing in place (same path, new bytes) invalidates the cache
    through its ``st_mtime_ns``/``st_size`` key.
    """
    try:
        stat = path.stat()
    except OSError:
        return detect_file_type_uncached(path)
    return _detect_cached(str(path), stat.st_mtime_ns, stat.st_size)
