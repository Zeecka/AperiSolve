"""Tests for the bring-your-own-key "Ask AI" panel.

Two layers: the server side (does the flag add or remove the panel, and does
the page stay free of provider hosts and key handling) and the browser side —
the panel's pure logic is exercised under node through
``tests/fixtures/ai_panel_probe.js``, because the digest truncation and the SSE
reassembly are where a silent wrong answer would come from.
"""

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

from aperisolve.i18n import js_catalog
from aperisolve.models import Image, Submission, db

IMG_HASH = "e" * 32
SUB_HASH = "f" * 32

REPO_ROOT = Path(__file__).resolve().parent.parent
PANEL_JS = REPO_ROOT / "aperisolve" / "static" / "js" / "ai_panel.js"
PROBE_JS = Path(__file__).parent / "fixtures" / "ai_panel_probe.js"

# Every LLM endpoint the panel can reach. None of them may appear in a page
# rendered by this server: the browser owns the provider call, the server does
# not know it happened.
PROVIDER_HOSTS = [
    "openrouter.ai",
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
]


@pytest.fixture
def seeded(app: Flask, tmp_path: Path) -> None:
    """Minimal Image + Submission pair so /<hash> renders."""
    stored = tmp_path / f"{IMG_HASH}.png"
    stored.write_bytes(b"\x89PNG\r\n\x1a\n")
    with app.app_context():
        db.session.add(Image(hash=IMG_HASH, file=str(stored), size=8, upload_count=1))
        db.session.add(
            Submission(
                hash=SUB_HASH,
                filename="secret.png",
                status="completed",
                date=time.time(),
                image_hash=IMG_HASH,
            ),
        )
        db.session.commit()


def _result_html(app: Flask, client: FlaskClient, *, enabled: int) -> str:
    app.config["AI_PANEL_ENABLED"] = enabled
    response = client.get(f"/{SUB_HASH}")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_panel_is_absent_when_the_flag_is_off(
    app: Flask,
    client: FlaskClient,
    seeded: None,
) -> None:
    """AI_PANEL_ENABLED=0 must leave no trace of the feature on the page."""
    html = _result_html(app, client, enabled=0)
    assert "ai_panel.js" not in html
    assert 'id="result-ai"' not in html
    assert "window.AI_PANEL_ENABLED = false" in html


def test_panel_is_present_when_the_flag_is_on(
    app: Flask,
    client: FlaskClient,
    seeded: None,
) -> None:
    """With the flag on, both the container and the versioned script render."""
    html = _result_html(app, client, enabled=1)
    assert 'id="result-ai"' in html
    assert "/static/js/ai_panel.js?v=" in html
    assert "window.AI_PANEL_ENABLED = true" in html


def test_panel_script_is_served_and_cacheable(client: FlaskClient) -> None:
    """The ?v= URL the template emits must resolve and get the immutable rule."""
    with client.get("/static/js/ai_panel.js?v=3.7.16") as response:
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"


def test_rendered_page_names_no_provider_and_carries_no_key(
    app: Flask,
    client: FlaskClient,
    seeded: None,
) -> None:
    """The server neither names a provider nor touches a key."""
    html = _result_html(app, client, enabled=1)
    for host in PROVIDER_HOSTS:
        assert host not in html, host
    assert "api_key" not in html.lower()


def test_no_new_route_was_added(app: Flask) -> None:
    """Track A adds zero server-side AI surface."""
    rules = [str(rule) for rule in app.url_map.iter_rules()]
    assert not [rule for rule in rules if "ai" in rule.lower().split("/")], rules


def test_security_headers_are_untouched(
    app: Flask,
    client: FlaskClient,
    seeded: None,
) -> None:
    """The panel must not relax the existing baseline hardening."""
    app.config["AI_PANEL_ENABLED"] = 1
    response = client.get(f"/{SUB_HASH}")
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_key_is_only_persisted_behind_the_remember_checkbox() -> None:
    """localStorage writes exist, and every one of them is gated on the box."""
    source = PANEL_JS.read_text(encoding="utf-8")
    assert source.count("localStorage.setItem") == 1
    assert source.count("localStorage.removeItem") == 1
    # Both branches present: ticked stores, unticked forgets.
    assert re.search(
        r"if \(rememberBox\.checked\) \{\s*\n\s*writeStoredKey\(key\);\s*\n\s*\} else \{"
        r"\s*\n\s*forgetStoredKey\(\);",
        source,
    ), "the ask handler must re-decide storage from the checkbox"
    assert "readStoredKey()" in source
    # A stored key pre-fills the field and re-ticks the box on reload.
    assert "rememberBox.checked = true" in source


def test_key_never_reaches_a_url_a_log_or_the_server() -> None:
    """The key is a header value and nothing else."""
    source = PANEL_JS.read_text(encoding="utf-8")
    assert not re.search(r"\bconsole\.\w+\(", source), "the panel must not log anything"
    # No same-origin request at all: every fetch target is provider-built.
    assert source.count("fetch(") == 1
    assert "fetch(request.url" in source
    for forbidden in ("?key=", "api_key=", "encodeURIComponent(key"):
        assert forbidden not in source, forbidden


def test_model_output_is_never_written_as_markup() -> None:
    """Streamed model text goes through textContent only."""
    source = PANEL_JS.read_text(encoding="utf-8")
    assert "answerEl.textContent" in source
    assert "answerEl.innerHTML" not in source
    # The only innerHTML writes are the panel's own static shell and the
    # provider/model option lists.
    assert sorted(re.findall(r"(\w+)\.innerHTML", source)) == [
        "modelList",
        "mount",
    ]


def test_every_panel_string_is_in_the_js_catalog(app: Flask) -> None:
    """A tr() key missing from js_catalog() would silently ship untranslated."""
    source = PANEL_JS.read_text(encoding="utf-8")
    used = set(re.findall(r'tr\(\s*"((?:[^"\\]|\\.)*)"', source))
    assert used, "no tr() calls found — did the panel stop using t()?"
    with app.test_request_context("/"):
        catalog = set(js_catalog())
    assert used <= catalog, sorted(used - catalog)


@pytest.fixture(scope="module")
def probe_facts() -> dict:
    """Run the browser-side logic under node and return its reported facts."""
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    completed = subprocess.run(  # noqa: S603 - fixed argv, repo-local script
        [shutil.which("node"), str(PROBE_JS)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_oversized_tool_output_is_truncated_head_and_tail(probe_facts: dict) -> None:
    """A 20 kB output is cut to its budget, keeping both ends and saying so."""
    facts = probe_facts["truncate"]
    assert facts["withinBudget"]
    assert facts["keptHead"]
    assert facts["keptTail"]
    assert re.fullmatch(r"\[\.\.\. \d+ lines omitted \.\.\.\]", facts["marker"]), facts["marker"]
    assert facts["unchangedWhenSmall"]
    # One enormous line has no lines to count, so the marker reports bytes
    # rather than claiming "0 lines omitted".
    assert re.fullmatch(r"\[\.\.\. \d+ bytes omitted \.\.\.\]", facts["singleLineMarker"])


def test_digest_stays_inside_its_budget_and_sends_no_image(probe_facts: dict) -> None:
    """The digest is capped, labelled untrusted, and lists images by name only."""
    facts = probe_facts["digest"]
    assert facts["withinTotalBudget"]
    assert facts["saysUntrusted"]
    assert facts["hasFileName"]
    assert facts["listsImageNameOnly"]
    assert facts["keepsEveryOrderedTool"]
    assert facts["skipsUnorderedTool"]
    assert facts["reportsToolError"]
    assert facts["truncatesBigTool"]
    assert facts["stringsHeadAndTail"]


def test_provider_requests_match_each_api(probe_facts: dict) -> None:
    """Three adapters, the documented auth per provider, and no Gemini."""
    facts = probe_facts["request"]
    assert facts["providers"] == ["openrouter", "openai", "anthropic", "custom"]
    assert facts["noGemini"]
    assert facts["anthropicUrl"] == "https://api.anthropic.com/v1/messages"
    assert facts["anthropicUsesXApiKey"]
    assert facts["anthropicSendsBrowserHeader"]
    assert facts["anthropicHasNoBearer"]
    assert facts["anthropicStreams"]
    assert facts["anthropicSystemIsPrompt"]
    assert facts["openaiUrl"] == "https://openrouter.ai/api/v1/chat/completions"
    assert facts["openaiBearer"]
    assert facts["openaiStreams"]
    assert facts["openaiSystemFirst"]
    assert facts["customEndpointFromBase"] == "http://localhost:11434/v1/chat/completions"
    assert facts["customEndpointNotDoubled"] == "http://x/v1/chat/completions"
    assert facts["customEndpointEmptyWithoutBase"] == ""
    assert facts["promptVersion"] >= 1
    assert facts["promptForbidsFollowingData"]


def test_streams_survive_frames_split_across_reads(probe_facts: dict) -> None:
    """A token split over two network reads must not be dropped or doubled."""
    assert probe_facts["streamOpenai"]["answer"] == "hello"
    assert probe_facts["streamOpenai"]["deltas"] == ["he", "llo"]
    assert probe_facts["streamAnthropic"]["answer"] == "ok"
    assert probe_facts["streamAnthropic"]["deltas"] == ["ok"]


def test_non_streaming_and_failing_providers_are_handled(probe_facts: dict) -> None:
    """A server that ignores stream:true still renders; an error surfaces."""
    assert probe_facts["streamNonSse"] == {"openai": "whole", "anthropic": "whole"}
    assert probe_facts["streamError"] == "insufficient credits"
