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
    "color_remapping",
    "file",
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
