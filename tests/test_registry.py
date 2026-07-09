"""Tests for analyzer auto-discovery and derived registry views."""

from aperisolve.analyzers.registry import (
    archive_tools,
    discover_analyzers,
    get_analyzers,
    tool_order,
)

# The historical frontend rendering order; new analyzers must be added here.
EXPECTED_TOOL_ORDER = [
    "decomposer",
    "spectrogram",
    "color_remapping",
    "file",
    "pdfinfo",
    "pdfid",
    "exiftool",
    "binwalk",
    "foremost",
    "outguess",
    "pngcheck",
    "pcrt",
    "identify",
    "steghide",
    "jpseek",
    "jsteg",
    "openstego",
    "zsteg",
    "strings",
]

EXPECTED_ARCHIVE_TOOLS = {
    "binwalk",
    "foremost",
    "steghide",
    "openstego",
    "pcrt",
    "jpseek",
    "outguess",  # regression: was missing from the old WORKER_FILES list
}

EXPECTED_PASSWORD_TOOLS = {"steghide", "openstego", "jpseek", "outguess"}

EXPECTED_DEEP_ONLY_TOOLS = {"outguess"}

# Analyzers grouped by their ``accepts`` gate (see aperisolve.filetype tags).
AGNOSTIC_TOOLS = {"file", "exiftool", "binwalk", "foremost", "strings"}
IMAGE_ONLY_TOOLS = {"decomposer", "color_remapping", "identify", "openstego"}
PNG_ONLY_TOOLS = {"pngcheck", "pcrt", "zsteg"}
JPEG_ONLY_TOOLS = {"jsteg", "jpseek", "outguess"}
AUDIO_ONLY_TOOLS = {"spectrogram"}
PDF_ONLY_TOOLS = {"pdfinfo", "pdfid"}


def test_discovery_finds_all_analyzers() -> None:
    """Every analyzer module registers exactly one analyzer."""
    assert sorted(cls.name for cls in discover_analyzers()) == sorted(EXPECTED_TOOL_ORDER)


def test_names_are_unique() -> None:
    """Duplicate names would silently merge results.json entries."""
    names = [cls.name for cls in discover_analyzers()]
    assert len(names) == len(set(names))


def test_template_analyzer_is_not_registered() -> None:
    """The template must never run in production."""
    assert "<toolname>" not in tool_order()


def test_tool_order_matches_frontend_history() -> None:
    """Rendering order must stay stable for users."""
    assert tool_order() == EXPECTED_TOOL_ORDER


def test_archive_tools_gate_downloads() -> None:
    """/download allow-list derives from has_archive."""
    assert archive_tools() == EXPECTED_ARCHIVE_TOOLS


def test_password_tools() -> None:
    """Password-aware analyzers receive the submission password."""
    assert {cls.name for cls in discover_analyzers() if cls.needs_password} == (
        EXPECTED_PASSWORD_TOOLS
    )


def test_deep_only_gating() -> None:
    """Deep-only analyzers run only for deep submissions."""
    normal = {cls.name for cls in get_analyzers(deep=False)}
    deep = {cls.name for cls in get_analyzers(deep=True)}
    assert deep - normal == EXPECTED_DEEP_ONLY_TOOLS
    assert deep == set(EXPECTED_TOOL_ORDER)


def test_tags_png_runs_agnostic_image_png() -> None:
    """A PNG upload gates to agnostic + image + png analyzers, no jpeg/steghide."""
    names = {cls.name for cls in get_analyzers(deep=True, tags=frozenset({"png", "image"}))}
    assert names == AGNOSTIC_TOOLS | IMAGE_ONLY_TOOLS | PNG_ONLY_TOOLS
    assert names.isdisjoint(JPEG_ONLY_TOOLS)
    assert "steghide" not in names


def test_tags_jpeg_runs_jpeg_and_steghide_no_png() -> None:
    """A JPEG upload gates to agnostic + image + jpeg + steghide, but not png."""
    names = {cls.name for cls in get_analyzers(deep=True, tags=frozenset({"jpeg", "image"}))}
    assert names == AGNOSTIC_TOOLS | IMAGE_ONLY_TOOLS | JPEG_ONLY_TOOLS | {"steghide"}
    assert names.isdisjoint(PNG_ONLY_TOOLS)


def test_tags_wav_runs_spectrogram_and_steghide_beyond_agnostic() -> None:
    """A WAV upload gates spectrogram (audio) + steghide (wav/au), no image tools."""
    names = {cls.name for cls in get_analyzers(deep=True, tags=frozenset({"wav", "audio"}))}
    assert names == AGNOSTIC_TOOLS | AUDIO_ONLY_TOOLS | {"steghide"}
    assert names.isdisjoint(IMAGE_ONLY_TOOLS | PNG_ONLY_TOOLS | JPEG_ONLY_TOOLS | PDF_ONLY_TOOLS)


def test_tags_pdf_runs_pdf_tools_only_beyond_agnostic() -> None:
    """A PDF upload gates the pdf tools in, but no image/audio/png/jpeg tools."""
    names = {cls.name for cls in get_analyzers(deep=True, tags=frozenset({"pdf"}))}
    assert names == AGNOSTIC_TOOLS | PDF_ONLY_TOOLS
    assert names.isdisjoint(
        IMAGE_ONLY_TOOLS | PNG_ONLY_TOOLS | JPEG_ONLY_TOOLS | AUDIO_ONLY_TOOLS | {"steghide"},
    )


def test_tags_empty_runs_only_agnostic() -> None:
    """An unclassifiable upload (empty tag set) runs only file-agnostic analyzers."""
    names = {cls.name for cls in get_analyzers(deep=True, tags=frozenset())}
    assert names == AGNOSTIC_TOOLS


def test_tags_none_matches_legacy() -> None:
    """tags=None disables the gate, preserving the pre-gate (deep-only) behavior."""
    for deep in (False, True):
        gated = [cls.name for cls in get_analyzers(deep=deep, tags=None)]
        legacy = [cls.name for cls in get_analyzers(deep=deep)]
        assert gated == legacy
