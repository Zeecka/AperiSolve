"""Internationalization helpers: locale selection, JS catalog, hreflang."""

from flask import Blueprint, g, request
from flask_babel import gettext as _

DEFAULT_LANG = "en"
# Languages served under a URL prefix (/fr/, /es/, ...). English is at the root.
PREFIX_LANGS = ["fr", "es", "de", "ru", "zh", "pt"]
SUPPORTED_LANGS = [DEFAULT_LANG, *PREFIX_LANGS]
LANG_PREFIX_RULE = f"/<any({','.join(PREFIX_LANGS)}):lang_code>"


def select_locale() -> str:
    """Locale precedence: URL prefix, then cookie, then Accept-Language."""
    lang = g.get("lang_code")
    if lang in SUPPORTED_LANGS:
        return lang
    cookie = request.cookies.get("lang")
    if cookie in SUPPORTED_LANGS:
        return cookie
    return request.accept_languages.best_match(SUPPORTED_LANGS) or DEFAULT_LANG


def register_lang_handling(blueprint: Blueprint) -> None:
    """Make a blueprint language-aware for its prefixed registration.

    The ``lang_code`` URL value is popped into ``g`` before views run, and
    re-injected by ``url_for`` so in-language navigation stays in-language.
    """

    @blueprint.url_value_preprocessor
    def pull_lang_code(_endpoint: str | None, values: dict | None) -> None:
        g.lang_code = values.pop("lang_code", None) if values else None

    @blueprint.url_defaults
    def add_lang_code(_endpoint: str, values: dict) -> None:
        if "lang_code" not in values and g.get("lang_code"):
            values["lang_code"] = g.lang_code


def lang_prefix() -> str:
    """URL prefix of the active language ("" for English)."""
    lang = g.get("lang_code")
    return f"/{lang}" if lang else ""


def alternates_for(bare_path: str, langs: list[str] | None = None) -> list[tuple[str, str]]:
    """Build hreflang (code, href) pairs for an unprefixed path."""
    pairs = [
        (lang, bare_path if lang == DEFAULT_LANG else f"/{lang}{bare_path}")
        for lang in (langs or SUPPORTED_LANGS)
    ]
    pairs.append(("x-default", bare_path))
    return pairs


def js_catalog() -> dict[str, str]:
    """Strings rendered client-side by aperisolve.js, keyed by English text."""
    return {
        "First upload:": _("First upload:"),
        "Last upload:": _("Last upload:"),
        "Name(s):": _("Name(s):"),
        "Size:": _("Size:"),
        "Upload count:": _("Upload count:"),
        "Common password(s):": _("Common password(s):"),
        "Remove password": _("Remove password"),
        "Remove Image": _("Remove Image"),
        "Available in {s} seconds": _("Available in {s} seconds"),
        "Image successfully removed": _("Image successfully removed"),
        "Network error occurred": _("Network error occurred"),
        "Error:": _("Error:"),
        "Download file": _("Download file"),
        "Superimposed": _("Superimposed"),
        "Red": _("Red"),
        "Green": _("Green"),
        "Blue": _("Blue"),
        "Alpha": _("Alpha"),
        "❌ Error during the analysis.": _("❌ Error during the analysis."),
        "Please select an image.": _("Please select an image."),
        "❌ Invalid server response: missing submission_hash.": _(
            "❌ Invalid server response: missing submission_hash.",
        ),
        "❌ Invalid server response.": _("❌ Invalid server response."),
        "❌ File too large. Please upload a smaller file.": _(
            "❌ File too large. Please upload a smaller file.",
        ),
        "Upload complete": _("Upload complete"),
        "❌ An error occurred during the transfer": _("❌ An error occurred during the transfer"),
    }
